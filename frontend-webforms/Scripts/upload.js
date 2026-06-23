
const stagingList = document.getElementById('stagingList');
const fileInput = document.getElementById('fileInput');
const stagingCardTemplate = document.getElementById('stagingCardTemplate');
const uploadDropzone = document.getElementById('uploadDropzone');
const uploadBtn = document.getElementById('uploadBtn');
const directoryInput = document.getElementById('directory');


const stagedFiles = new Map();

fileInput.addEventListener('change',  (e) => {
    const files = [...e.target.files];

    processIncomingFiles(files);

    e.target.value = '';
});

uploadDropzone.addEventListener('dragover', handleDragOverZone);
uploadDropzone.addEventListener('drop', handleDrop);

window.addEventListener('dragover', preventGlobalDrag);
window.addEventListener('drop', preventGlobalDrop);

uploadBtn.addEventListener('click', () => processUploadQueue());
stagingList.addEventListener('click', handleStagingAction);


function openFileDialog() {
    fileInput.click();
}
async function processIncomingFiles(files) {
    const MAX_ZIP_SIZE = 500 * 1024 * 1024; // 500MB Limit

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        if (file.name.toLowerCase().endsWith('.zip') || file.type === 'application/zip') {

            if (file.size > MAX_ZIP_SIZE) {
                alert(`The ZIP file "${file.name}" is too large to extract in the browser. Please unzip it on your computer and upload the files directly.`);
                continue;
            }

            // Create a temporary UI card for the ZIP itself
            const zipId = getUUID();
            createStagingCard(file.name, formatFileSize(file.size), zipId);

            const zipCard = stagingList.querySelector(`.staging-card[data-id="${zipId}"]`);
            if (zipCard) {
                zipCard.setAttribute('data-state', 'processing');
                zipCard.querySelector('.staging-status-pill').textContent = "Extracting";
                zipCard.querySelector('.staging-status-text').textContent = "Unpacking files...";
            }

            await extractZip(file, zipCard);

        } else {
            handleFile(file);
        }
    }
}

function handleFile(file) {
    const id = getUUID();
    createStagingCard(file.name, formatFileSize(file.size), id);
    stagedFiles.set(id, file);
}

async function extractZip(zipFile, zipCard) {
    try {
        if (typeof JSZip === 'undefined') {
            throw new Error("JSZip library not loaded");
        }

        const zip = new JSZip();
        const loadedZip = await zip.loadAsync(zipFile);
        const extractionPromises = [];

        loadedZip.forEach((relativePath, zipEntry) => {
            const filename = zipEntry.name.split('/').pop();

            if (zipEntry.dir || relativePath.includes('__MACOSX/') || filename.startsWith('.')) {
                return;
            }

            const extractPromise = zipEntry.async('blob').then(blob => {
                const extractedFile = new File([blob], filename, {
                    type: blob.type || 'application/octet-stream',
                    lastModified: zipEntry.date.getTime()
                });

                handleFile(extractedFile);
            });

            extractionPromises.push(extractPromise);
        });

        // Wait for all internal files to finish extracting
        await Promise.all(extractionPromises);

        if (zipCard) {
            zipCard.remove();
        }

    } catch (error) {
        console.error("Failed to extract zip:", error);

        if (zipCard) {
            zipCard.setAttribute('data-state', 'error');
            zipCard.querySelector('.staging-status-pill').textContent = "Error";
            zipCard.querySelector('.staging-status-text').textContent = "Failed to extract: Encrypted or corrupted";
        }
    }
}

async function processUploadQueue(queue = stagedFiles) {
    const category = directoryInput.value;

    for (const [id, file] of queue) {
        const card = stagingList.querySelector(`.staging-card[data-id="${id}"]`);

        if (!card || card.getAttribute('data-state') !== 'pending') {
            continue;
        }

        card.setAttribute('data-state', 'uploading');
        card.querySelector('.staging-status-pill').textContent = "Uploading";

        try {
            const documentId = await uploadSingleFile(file, category);
            trackDocumentProgress(documentId, card);
        } catch (error) {
            console.error(error);
            card.setAttribute('data-state', 'error');
            card.querySelector('.staging-status-pill').textContent = "Error";
            card.querySelector('.staging-status-text').textContent = "Upload failed " + error.message.substring(0, 100);
        }
    }
}

async function uploadSingleFile(file, category) {
    const formData = new FormData();
    formData.append('file', file);
    if (category) formData.append('category', category);

    const response = await fetch(`${apiBaseURL}/documents`, {
        method: 'POST',
        credentials: "include",
        body: formData
    });
    if (response.status !== 202) {
        const errorData = await response.json();
        const errorMessage = errorData.detail || 'Server rejected the upload';
        throw new Error(errorMessage);
    }
    const data = await response.json();
    return data.document_id;
}

function trackDocumentProgress(documentId, cardElement) {
    const eventSource = new EventSource(`${apiBaseURL}/documents/${documentId}/events`);

    eventSource.onmessage = function (event) {
        const data = JSON.parse(event.data);

        if (data.status === 'processing') {
            cardElement.setAttribute('data-state', 'processing');
            cardElement.querySelector('.staging-status-pill').textContent = "Processing";
            cardElement.querySelector('.staging-status-text').textContent = data.message || "Processing...";

        } else if (data.status === 'completed') {
            cardElement.setAttribute('data-state', 'success');
            cardElement.querySelector('.staging-status-pill').textContent = "Completed";
            cardElement.querySelector('.staging-status-text').textContent = "Vaulted successfully";
            eventSource.close();

        } else if (data.status === 'error') {
            cardElement.setAttribute('data-state', 'error');
            cardElement.querySelector('.staging-status-pill').textContent = "Error";
            cardElement.querySelector('.staging-status-text').textContent = data.message || "Processing error";
            eventSource.close();
        }
    };

    eventSource.onerror = function () {
        if (eventSource.readyState === EventSource.CONNECTING) {
            console.warn(`Connection disrupted for document ${documentId}. Retrying...`);

            cardElement.querySelector('.staging-status-text').textContent = "Reconnecting...";

        } else {
            console.error(`SSE connection completely failed for document: ${documentId}`);
            cardElement.setAttribute('data-state', 'error');
            cardElement.querySelector('.staging-status-pill').textContent = "Error";
            cardElement.querySelector('.staging-status-text').textContent = "Connection completely lost";

            eventSource.close();
        }
    };
};


function handleStagingAction(event) {
    const actionBtn = event.target.closest('.staging-card-action');
    if (!actionBtn) return;

    const card = actionBtn.closest('.staging-card');
    const id = card.getAttribute('data-id');

    if (event.target.closest('.staging-action-delete') || event.target.closest('.staging-action-success')) {
        stagedFiles.delete(id);
        card.remove();
    } else if (event.target.closest('.staging-action-cancel')) {
        // Implement cancel logic
    } else if (event.target.closest('.staging-action-retry')) {
        card.setAttribute('data-state', 'pending');

        const statusText = card.querySelector('.staging-status-text');
        if (statusText) statusText.textContent = 'Ready to upload';

        processUploadQueue(new Map([[id, stagedFiles.get(id)]]));
    }
}


function getDraggedFiles(dataTransfer) {
    return [...dataTransfer.items].filter(item => item.kind === "file");
}

function handleDragOverZone(e) {
    if (getDraggedFiles(e.dataTransfer).length > 0) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
    }
}

function handleDrop(e) {
    const fileItems = getDraggedFiles(e.dataTransfer);
    if (fileItems.length > 0) {
        e.preventDefault();

        const files = fileItems.map(item => item.getAsFile());

        processIncomingFiles(files);
    }
}

function preventGlobalDrag(e) {
    if (getDraggedFiles(e.dataTransfer).length > 0) {
        e.preventDefault();
        if (!uploadDropzone.contains(e.target)) {
            e.dataTransfer.dropEffect = "none";
        }
    }
}

function preventGlobalDrop(e) {
    if (getDraggedFiles(e.dataTransfer).length > 0) {
        e.preventDefault();
    }
}

function createStagingCard(filename, filesize, id) {
    const clone = stagingCardTemplate.content.cloneNode(true);
    const card = clone.querySelector('.staging-card');
    card.setAttribute('data-id', id);
    card.setAttribute('data-state', 'pending');

    clone.querySelector('.staging-filesize').textContent = filesize;
    clone.querySelector('.staging-filename').textContent = filename;

    stagingList.appendChild(clone);
}

function getUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}