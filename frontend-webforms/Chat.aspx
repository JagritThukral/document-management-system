<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Chat.aspx.cs" Inherits="HawkinsDMS.Chat" MasterPageFile="~/Site.Master" %>

<asp:Content ID="head" ContentPlaceHolderID="head" runat="server">
    <link rel="stylesheet" href="<%=ResolveUrl("~/Content/chat.css")%>" />
    <script src="<%=ResolveUrl("~/Scripts/chat.js")%>" defer></script>
</asp:Content>
<asp:Content ID="ChatContent" ContentPlaceHolderID="MainContent" runat="server">
    <h1 class="page-header">Chat with your documents</h1>
    <div class="chat-container">
        <div class="messages" id="messages"></div>
        <form id="chatForm" class="chat-form">
            <input type="text" id="userInput" placeholder="Ask a question about your documents..." autocomplete="off" required />
            <button type="submit">
                <svg role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                    <path d="M120-160v-640h720v640H120Zm360-80q17 0 28.5-11.5T520-280v-80L168-736q-15-20-4.5-42t36.5-22h560q26 0 36.5 22t-4.5 42L560-440v80q0 17-11.5 28.5T520-240h-40Z"></path>
                </svg>
            </button>
        </form>
    </div>
</asp:Content>
