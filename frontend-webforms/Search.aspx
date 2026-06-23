<%@ Page Language="C#" AutoEventWireup="true" MasterPageFile="~/Site.Master" CodeBehind="Search.aspx.cs" Inherits="HawkinsDMS.Search" %>

<asp:Content ID="head" ContentPlaceHolderID="head" runat="server">
    <link rel="stylesheet" href="<%=ResolveUrl("~/Content/search.css") %>" />
    <script src="<%=ResolveUrl("~/Scripts/search.js") %>" defer></script>
</asp:Content>

<asp:Content ID="BodyContent" ContentPlaceHolderID="MainContent" runat="server">
    <div class="search-wrapper">

        <div class="hero-content">
            <h1 class="page-header">What are you looking for?</h1>
            <p class="sub-header">Search through all documents in the vault.</p>
        </div>

        <div class="search-controls">
            <button class="back-button" onclick="closeSearch()">
                <svg role="img" data-slot="icon" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path clip-rule="evenodd" fill-rule="evenodd" d="M11.03 3.97a.75.75 0 0 1 0 1.06l-6.22 6.22H21a.75.75 0 0 1 0 1.5H4.81l6.22 6.22a.75.75 0 1 1-1.06 1.06l-7.5-7.5a.75.75 0 0 1 0-1.06l7.5-7.5a.75.75 0 0 1 1.06 0Z"></path>
                </svg>
                <span>Back To Search</span>
            </button>

            <div class="search-group">
                <svg class="search-icon" role="img" data-slot="icon" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path clip-rule="evenodd" fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 0 13.5 6.75 6.75 0 0 0 0-13.5ZM2.25 10.5a8.25 8.25 0 1 1 14.59 5.28l4.69 4.69a.75.75 0 1 1-1.06 1.06l-4.69-4.69A8.25 8.25 0 0 1 2.25 10.5Z"></path>
                </svg>
                <input type="text" id="searchInput" placeholder="Type to search. Use keywords, phrases..." class="search-input" />
            </div>
            <button class="ask-ai" onclick="redirectToAIChat();">
                <svg class="ask-ai__icon" role="img" data-slot="icon" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path clip-rule="evenodd" fill-rule="evenodd" d="M9 4.5a.75.75 0 0 1 .721.544l.813 2.846a3.75 3.75 0 0 0 2.576 2.576l2.846.813a.75.75 0 0 1 0 1.442l-2.846.813a3.75 3.75 0 0 0-2.576 2.576l-.813 2.846a.75.75 0 0 1-1.442 0l-.813-2.846a3.75 3.75 0 0 0-2.576-2.576l-2.846-.813a.75.75 0 0 1 0-1.442l2.846-.813A3.75 3.75 0 0 0 7.466 7.89l.813-2.846A.75.75 0 0 1 9 4.5ZM18 1.5a.75.75 0 0 1 .728.568l.258 1.036c.236.94.97 1.674 1.91 1.91l1.036.258a.75.75 0 0 1 0 1.456l-1.036.258c-.94.236-1.674.97-1.91 1.91l-.258 1.036a.75.75 0 0 1-1.456 0l-.258-1.036a2.625 2.625 0 0 0-1.91-1.91l-1.036-.258a.75.75 0 0 1 0-1.456l1.036-.258a2.625 2.625 0 0 0 1.91-1.91l.258-1.036A.75.75 0 0 1 18 1.5ZM16.5 15a.75.75 0 0 1 .712.513l.394 1.183c.15.447.5.799.948.948l1.183.395a.75.75 0 0 1 0 1.422l-1.183.395c-.447.15-.799.5-.948.948l-.395 1.183a.75.75 0 0 1-1.422 0l-.395-1.183a1.5 1.5 0 0 0-.948-.948l-1.183-.395a.75.75 0 0 1 0-1.422l1.183-.395c.447-.15.799-.5.948-.948l.395-1.183A.75.75 0 0 1 16.5 15Z"></path>
                </svg>
                <span>Ask AI</span>
            </button>
        </div>
    </div>
    <div class="search-spacer"></div>
    <div class="results">
        <div class="results-view" id="hybridView" data-state="loading">
            <div class="results-view__header">
                <h2 class="results-view__title">
                    <svg class="results-view__icon" role="img" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                        <path d="M784-120 532-372q-30 24-69 38t-83 14q-109 0-184.5-75.5T120-580q0-109 75.5-184.5T380-840q109 0 184.5 75.5T640-580q0 44-14 83t-38 69l252 252-56 56ZM380-400q75 0 127.5-52.5T560-580q0-75-52.5-127.5T380-760q-75 0-127.5 52.5T200-580q0 75 52.5 127.5T380-400Z" />
                    </svg><span>Search Results</span>
                </h2>
                <span class="result-count" id="hybridResultsCount"></span>
                <span class="text-loader">Searching Vault...</span>
            </div>

            <div class="results-view__content">
                <div class="results-skeleton-container" id="hybridSkeletons">
                    <div class="skeleton-card">
                        <div class="skeleton-card__info">
                            <div class="skeleton-icon skeleton-shimmer"></div>
                            <div class="skeleton-card__content">
                                <div class="skeleton-title skeleton-shimmer"></div>
                                <div class="skeleton-snippet skeleton-shimmer"></div>
                                <div class="skeleton-snippet short skeleton-shimmer"></div>
                            </div>
                        </div>
                        <div class="skeleton-action skeleton-shimmer"></div>
                    </div>
                    <div class="skeleton-card">
                        <div class="skeleton-card__info">
                            <div class="skeleton-icon skeleton-shimmer"></div>
                            <div class="skeleton-card__content">
                                <div class="skeleton-title skeleton-shimmer" style="width: 50%;"></div>
                                <div class="skeleton-snippet skeleton-shimmer"></div>
                                <div class="skeleton-snippet short skeleton-shimmer" style="width: 70%;"></div>
                            </div>
                        </div>
                        <div class="skeleton-action skeleton-shimmer"></div>
                    </div>
                </div>
                <div class="results-empty" id="hybridEmpty">No results found in the vault.</div>
                <div class="results-error" id="hybridErrorMsg"></div>
                <div class="results-container" id="hybridResults"></div>
            </div>
        </div>
    </div>
    <template id="resultCardTemplate">
        <a class="results-card" href="<%= ConfigurationManager.AppSettings["ApiBaseUrl"] %>/documents/">
            <div class="results-card__info">
                <img class="results-card__icon" src="Assets/docs/pdf.svg" />
                <div class="results-card__content">
                    <h3 class="results-card__title">Document Title.pdf</h3>
                    <p class="results-card__snippet">This is a snippet from the document that shows how the search term was found in the content...</p>
                </div>
            </div>
            <img class="results-card__icon" src="Assets/icons/EllipsisVertical.svg" />
        </a>
    </template>
</asp:Content>
