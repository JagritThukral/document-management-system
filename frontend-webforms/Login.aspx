<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Login.aspx.cs" Inherits="HawkinsDMS.Login" MasterPageFile="~/Site.Master" %>

<asp:Content ID="head" ContentPlaceHolderID="head" runat="server">
    <script defer src="<%= ResolveUrl("~/Scripts/login.js") %>"></script>
    <link rel="stylesheet" href="<%= ResolveUrl("~/Content/login.css") %>" />
</asp:Content>
<asp:Content ID="LoginContent" ContentPlaceHolderID="MainContent" runat="server">
    <section class="login-card">
        <svg class="login-icon" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
            <path d="M234-276q51-39 114-61.5T480-360q69 0 132 22.5T726-276q35-41 54.5-93T800-480q0-133-93.5-226.5T480-800q-133 0-226.5 93.5T160-480q0 59 19.5 111t54.5 93Zm146.5-204.5Q340-521 340-580t40.5-99.5Q421-720 480-720t99.5 40.5Q620-639 620-580t-40.5 99.5Q539-440 480-440t-99.5-40.5ZM480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm100-95.5q47-15.5 86-44.5-39-29-86-44.5T480-280q-53 0-100 15.5T294-220q39 29 86 44.5T480-160q53 0 100-15.5ZM523-537q17-17 17-43t-17-43q-17-17-43-17t-43 17q-17 17-17 43t17 43q17 17 43 17t43-17Zm-43-43Zm0 360Z" />
        </svg>
        <div class="login-badge">
            <svg class="badge-icon" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
                <path d="M480-80q-139-35-229.5-159.5T160-516v-244l320-120 320 120v244q0 152-90.5 276.5T480-80Zm0-84q97-30 162-118.5T718-480H480v-315l-240 90v207q0 7 2 18h238v316Z" />
            </svg>
            <p class="badge-text">secure login</p>
        </div>
        <form id="loginForm" class="login-form">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" placeholder="staff@hawkinscookers.com" autocomplete="off" required />
            <label for="password">Password</label>
            <input type="password" id="password" name="password" placeholder="********" autocomplete="off" required />
            <button type="submit" >Login</button>
        </form>
    </section>
</asp:Content>