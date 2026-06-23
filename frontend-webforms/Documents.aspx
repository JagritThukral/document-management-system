<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Documents.aspx.cs" Inherits="HawkinsDMS.Documents" MasterPageFile="~/Site.Master" %>

<asp:Content ID="head" ContentPlaceHolderID="head" runat="server">
    <link rel="stylesheet" href="<%=ResolveUrl("~/Content/documents.css")%>" />
    <script src="<%=ResolveUrl("~/Scripts/documents.js")%>" defer></script>
</asp:Content>
<asp:Content ID="DocumentsContent" ContentPlaceHolderID="MainContent" runat="server">
    <div class="page-header-container">
        <div class="header-titles">
            <h2 class="page-header" id="currentPathTitle">All Documents</h2>
            <p class="sub-header" id="documentCount">Loading...</p>
        </div>
        <div class="header-actions">
            <div class="toggle-group">
                <button class="toggle-btn active" type="button">
                    <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                        <path d="M120-320v-80h720v80H120Zm0-160v-80h720v80H120Zm0-160v-80h720v80H120Zm0 480v-80h720v80H120Z" />
                    </svg>
                </button>
                <button class="toggle-btn" type="button">
                    <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                        <path d="M120-520v-320h320v320H120Zm0 400v-320h320v320H120Zm400-400v-320h320v320H520Zm0 400v-320h320v320H520Z" />
                    </svg>
                </button>
            </div>
            <button class="btn-outline" type="button">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="M440-160q-17 0-28.5-11.5T400-200v-240L168-736q-15-20-4.5-42t36.5-22h560q26 0 36.5 22t-4.5 42L560-440v240q0 17-11.5 28.5T520-160h-80Z" />
                </svg>
                Filter
            </button>
        </div>
    </div>

    <section class="documents-table-container">
        <table class="documents-table" id="documents">
            <thead>
                <tr>
                    <th class="col-checkbox">
                        <input type="checkbox" id="selectAll" /></th>
                    <th class="col-name">Name</th>
                    <th class="col-size">Size</th>
                    <th class="col-modified">Last Modified</th>
                    <th class="col-actions"></th>
                </tr>
            </thead>
            <tbody id="documentList">
            </tbody>
        </table>
    </section>

    <template id="documentRowTemplate">
        <tr>
            <td class="col-checkbox">
                <input type="checkbox" class="row-checkbox" /></td>
            <td class="name-cell">
                <img src="" class="file-icon" alt="icon" />
                <span class="file-name"></span>
            </td>
            <td><span class="size-pill"></span></td>
            <td class="modified-cell"></td>
            <td class="col-actions">
                <button class="action-btn" type="button">
                    <svg role="img" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                        <path d="M480-160q-33 0-56.5-23.5T400-240q0-33 23.5-56.5T480-320q33 0 56.5 23.5T560-240q0 33-23.5 56.5T480-160Zm0-240q-33 0-56.5-23.5T400-480q0-33 23.5-56.5T480-560q33 0 56.5 23.5T560-480q0 33-23.5 56.5T480-400Zm0-240q-33 0-56.5-23.5T400-720q0-33 23.5-56.5T480-800q33 0 56.5 23.5T560-720q0 33-23.5 56.5T480-640Z" />
                    </svg>
                </button>
            </td>
        </tr>
    </template>
</asp:Content>