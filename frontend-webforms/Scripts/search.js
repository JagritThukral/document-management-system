console.log('Api URL:', apiBaseURL);
const searchInput = document.getElementById('searchInput');

const hybridView = document.getElementById('hybridView');
const hybridContainer = document.getElementById('hybridResults');
const hybridCountEl = document.getElementById('hybridResultsCount');
const hybridErrorMsgEl = document.getElementById('hybridErrorMsg');

const template = document.getElementById('resultCardTemplate')

searchInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
            document.documentElement.classList.add('search-active');
            loadSearchData(query);
        }
    }
});

function redirectToAIChat() {
    const query = searchInput.value.trim();
    const encodedQuery = encodeURIComponent(query);
    window.location.href = `/chat${query ? '?query=' + encodedQuery : ''}`;
}
function closeSearch() {
    searchInput.value = '';
    document.documentElement.classList.remove('search-active');
}
async function loadSearchData(query) {
    const searchStart = performance.now();
    hybridView.setAttribute('data-state', 'loading');

    try {
        const response = await fetch(`${apiBaseURL}/search?query=${encodeURIComponent(query)}&limit=15`, {
            method: "GET",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
            },
        });
        const data = await response.json();

        const searchEnd = performance.now();
        const duration = ((searchEnd - searchStart) / 1000).toFixed(2);
        console.log(`Hybrid search resolved in ${duration} seconds`);

        if (data.status === "error") throw new Error("Server returned an error state.");

        handleSearchData(data, hybridView, hybridContainer, hybridCountEl);

    } catch (error) {
        console.error('Error fetching hybrid search results:', error);
        hybridView.setAttribute('data-state', 'error');
        hybridErrorMsgEl.textContent = 'An error occurred while fetching search results. Please try again.';
    }
}

function handleSearchData(data, view, container, countEl) {
    container.innerHTML = '';

    if (!data || !data.results || data.results.length === 0) {
        countEl.textContent = '0';
        view.setAttribute('data-state', 'empty');
        return;
    }

    countEl.textContent = data.results.length;
    const masterFragment = document.createDocumentFragment();

    data.results.forEach(result => {
        const fileExtension = result.filename.split('.').pop().toLowerCase();
        const clone = template.content.cloneNode(true);

        const cardLink = clone.querySelector('.results-card');
        cardLink.setAttribute('href', `${apiBaseURL}/documents/${result.document_id}`);
        clone.querySelector('.results-card__title').textContent = result.filename;

        const snippetEl = clone.querySelector('.results-card__snippet');

        // Smart display: If we have an exact keyword snippet, use it. Otherwise, use the raw chunk.
        if (result.snippet) {
            buildKeywordSnippet(result.snippet, snippetEl);
        } else {
            snippetEl.textContent = result.chunk_text;
            snippetEl.classList.add('semantic-clamp');
        }

        // Assuming getIconUrl is defined elsewhere in your scripts
        const iconSrc = getIconUrl(fileExtension);
        clone.querySelector('.results-card__icon').setAttribute('src', iconSrc);

        masterFragment.appendChild(clone);
    });

    container.appendChild(masterFragment);
    view.setAttribute('data-state', 'success');
}
function buildKeywordSnippet(text, snippetEL) {
    // 1. Clear any placeholder text
    snippetEL.textContent = '';

    // 2. Safety check
    if (!text) return;

    // 3. Split the text exactly at the bold tags
    const parts = text.split(/(<b>|<\/b>)/g);
    let isBold = false;

    parts.forEach(part => {
        if (part === '<b>') {
            isBold = true;
        } else if (part === '</b>') {
            isBold = false;
        } else if (part) { // If there is actual text
            if (isBold) {
                const highlight = document.createElement('span');
                highlight.textContent = part;
                snippetEL.appendChild(highlight);
            } else {
                // Append normal text securely
                snippetEL.appendChild(document.createTextNode(part));
            }
        }
    });
}
