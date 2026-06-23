<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Upload.aspx.cs" Inherits="HawkinsDMS.Upload" MasterPageFile="~/Site.Master" %>

<asp:Content ID="head" ContentPlaceHolderID="head" runat="server">
    <link rel="stylesheet" href="<%= Page.ResolveUrl("~/Content/upload.css") %>" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script defer src="<%= Page.ResolveUrl("~/Scripts/upload.js") %>"></script>

</asp:Content>
<asp:Content ID="UploadContent" ContentPlaceHolderID="MainContent" runat="server">
    <h1 class="page-header">Upload</h1>
    <h2 class="sub-header">Upload a file to the vault</h2>
    <div class="upload-container">
        <section class="upload-dropzone" id="uploadDropzone">
            <div class="upload-icon">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
                    <path d="M260-160q-91 0-155.5-63T40-377q0-78 47-139t123-78q25-92 100-149t170-57q117 0 198.5 81.5T760-520q69 8 114.5 59.5T920-340q0 75-52.5 127.5T740-160H520q-33 0-56.5-23.5T440-240v-206l-64 62-56-56 160-160 160 160-56 56-64-62v206h220q42 0 71-29t29-71q0-42-29-71t-71-29h-60v-80q0-83-58.5-141.5T480-720q-83 0-141.5 58.5T280-520h-20q-58 0-99 41t-41 99q0 58 41 99t99 41h100v80H260Zm220-280Z" />
                </svg>
            </div>
            <h3 class="upload-text">Drag & Drop files here</h3>
            <p class="upload-subtext">Supports 30+ formats including PDF, Word (DOC/DOCX), Excel (XLS/XLSX), PowerPoint (PPT/PPTX), Images (PNG/JPG/HEIC), Emails (EML/MSG), HTML, Markdown, and more.</p>
            <div class="upload-divider-container">
                <span class="upload-divider"></span>
                <span class="upload-divider-text">or</span>
                <span class="upload-divider"></span>
            </div>
            <button id="fileSelectButton" class="upload-button" onclick="openFileDialog()">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="M160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h240l80 80h320q33 0 56.5 23.5T880-640H447l-80-80H160v480l96-320h684L837-217q-8 26-29.5 41.5T760-160H160Zm84-80h516l72-240H316l-72 240Zm0 0 72-240-72 240Zm-84-400v-80 80Z" />
                </svg>Select Files</button>
            <input class="file-input" id="fileInput" type="file" multiple style="display: none;" />
        </section>
        <aside class="upload-settings-container">
            <div class="upload-settings">
                <h3 class="settings-header">Upload Settings</h3>
                <div class="setting-group">
                    <label for="directory" class="directory-label">Directory</label>
                    <input class="directory-input" id="directory" type="text" placeholder="Enter document directory" />
                </div>
                <button id="uploadBtn" class="upload-button">
                    <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
                        <path d="M440-320v-326L336-542l-56-58 200-200 200 200-56 58-104-104v326h-80ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z" />
                    </svg>
                    Upload
                </button>
            </div>
        </aside>
        <section class="staging-section">
            <h3 class="staging-header">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
                    <path d="M440-280h80v-168l64 64 56-56-160-160-160 160 56 56 64-64v168ZM160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h240l80 80h320q33 0 56.5 23.5T880-640v400q0 33-23.5 56.5T800-160H160Zm0-80h640v-400H447l-80-80H160v480Zm0 0v-480 480Z" />
                </svg>Staged Files</h3>
            <div class="staging-list" id="stagingList">
            </div>
        </section>
    </div>
    <template id="stagingCardTemplate">
        <div class="staging-card" data-state="pending">
            <div class="staging-card-icon">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
                    <path d="M440-200h80v-167l64 64 56-57-160-160-160 160 57 56 63-63v167ZM240-80q-33 0-56.5-23.5T160-160v-640q0-33 23.5-56.5T240-880h320l240 240v480q0 33-23.5 56.5T720-80H240Zm280-520v-200H240v640h480v-440H520ZM240-800v200-200 640-640Z" />
                </svg>
            </div>

            <div class="staging-card-content">
                <div class="staging-card-row">
                    <p class="staging-filename">Document.pdf</p>
                    <span class="staging-status-pill">Pending</span>
                </div>
                <span class="staging-filesize">2.3 MB</span>
                <p class="staging-status-text">Ready to upload</p>
                <div class="staging-progress-track">
                    <div class="staging-progress-fill" style="width: 50%;">
                    </div>
                </div>
            </div>
            <button class="staging-card-action">
                <svg class="staging-action-delete" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="M280-120q-33 0-56.5-23.5T200-200v-520h-40v-80h200v-40h240v40h200v80h-40v520q0 33-23.5 56.5T680-120H280Zm400-600H280v520h400v-520ZM360-280h80v-360h-80v360Zm160 0h80v-360h-80v360ZM280-720v520-520Z" />
                </svg>
                <svg class="staging-action-cancel" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="m336-280 144-144 144 144 56-56-144-144 144-144-56-56-144 144-144-144-56 56 144 144-144 144 56 56ZM480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z" />
                </svg>
                <svg class="staging-action-retry" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="M480-160q-134 0-227-93t-93-227q0-134 93-227t227-93q69 0 132 28.5T720-690v-110h80v280H520v-80h168q-32-56-87.5-88T480-720q-100 0-170 70t-70 170q0 100 70 170t170 70q77 0 139-44t87-116h84q-28 106-114 173t-196 67Z" />
                </svg>
                <svg class="staging-action-success" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="m424-296 282-282-56-56-226 226-114-114-56 56 170 170Zm56 216q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z" />
                </svg>
            </button>
        </div>

    </template>
</asp:Content>
