const currentPath = window.location.pathname.toLowerCase();

const sidebar = document.getElementById("sidebar");
const toggleBtnSvg = document.querySelector('.toggle-btn svg');
const navLinks = document.querySelectorAll('.sidebar__link');

navLinks.forEach(link => {
    const linkPath = new URL(link.href).pathname.toLowerCase();
    if (currentPath === linkPath) {
        link.parentElement.classList.add("sidebar__item--active");
    }
});

function toggleAccountMenu() {
    document.documentElement.classList.toggle("show-account-menu")
}
function login() {
    window.location.href = "/login";
}
function logout() {
    deleteCookie("access_token");
    window.location.href = "/"
}
function toggleSidebar() {
    const isCollapsed = document.documentElement.classList.toggle("sidebar-collapsed");
    document.cookie = `sidebar_collapsed=${isCollapsed}; path=/; SameSite=Lax`;
}
const extensionMap = {
    'pdf': 'pdf',
    'png': 'img', 'jpg': 'img', 'jpeg': 'img', 'heic': 'img', 'bmp': 'img', 'tiff': 'img', 'prn': 'img',
    'docx': 'doc', 'doc': 'doc', 'odt': 'doc', 'dot': 'doc', 'dotm': 'doc', 'abw': 'doc', 'hwp': 'doc',
    'xlsx': 'sheet', 'xls': 'sheet', 'csv': 'sheet', 'tsv': 'sheet', 'fods': 'sheet', 'et': 'sheet', 'mw': 'sheet',
    'html': 'web', 'htm': 'web', 'xml': 'web', 'epub': 'web',
    'pptx': 'slide', 'ppt': 'slide', 'pot': 'slide', 'pptm': 'slide',
    'eml': 'email', 'msg': 'email',
    'txt': 'text', 'rtf': 'text', 'rst': 'text', 'org': 'text',
    'md': 'markdown',
};
function getIconUrl(extension) {
    const ext = extension.toLowerCase();

    const categoryName = extensionMap[ext] || 'file';

    return `/assets/docs/${categoryName}.svg`;
}
function formatFileSize(size) {
    size = +size; // autobox to number primitive
    if (isNaN(size) || size < 0) return '0B';

    const filesSizes = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (size / 1024 >= 1 && i < filesSizes.length - 1) {
        size /= 1024;
        i++;
    }
    return `${parseFloat(size.toFixed(2))}${filesSizes[i]}`;
}
function deleteCookie(name, path = '/', domain = '') {
    if (hasCookie(name)) {
        let cookieString = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path};`;
        if (domain) {
            cookieString += ` domain=${domain};`;
        }
        document.cookie = cookieString;
    }
}