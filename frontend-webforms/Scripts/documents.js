let currentpath = "";

document.addEventListener("DOMContentLoaded", () => {
  fetchDocuments(currentpath);

  const selectAll = document.getElementById("selectAll");
  if (selectAll) {
    selectAll.addEventListener("change", (e) => {
      const checkboxes = document.querySelectorAll(".row-checkbox");
      checkboxes.forEach((cb) => {
        cb.checked = e.target.checked;
        const row = cb.closest("tr");
        if (e.target.checked) row.classList.add("row-selected");
        else row.classList.remove("row-selected");
      });
    });
  }
});

async function fetchDocuments(path) {
  try {
    const response = await fetch(
      `${apiBaseURL}/documents?path=${encodeURIComponent(path)}`,
      {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
    const result = await response.json();

    document.getElementById("documentCount").textContent =
      `${result.count || 0} items found`;
    document.getElementById("currentPathTitle").textContent =
      path === "" ? "All Documents" : path;

    currentpath = result.current_path || path;
    renderDocuments(result.data, currentpath);
  } catch (error) {
    console.error(error);
  }
}

function renderDocuments(data, path) {
  const tbody = document.getElementById("documentList");
  const template = document.getElementById("documentRowTemplate");

  tbody.innerHTML = "";

  if (path !== "") {
    const upRow = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.innerHTML = `<span style="cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 0.5rem;" onclick="navigateUp()">
            <svg role="img" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor">
                <path d="M400-240 160-480l240-240 56 58-142 142h486v80H314l142 142-56 58Z"/>
            </svg> Back
        </span>`;
    upRow.appendChild(td);
    tbody.appendChild(upRow);
  }

  data.forEach((item) => {
    const clone = template.content.cloneNode(true);
    const tr = clone.querySelector("tr");
    const checkbox = clone.querySelector(".row-checkbox");
    const nameSpan = clone.querySelector(".file-name");
    const iconImg = clone.querySelector(".file-icon");
    const pillSpan = clone.querySelector(".size-pill");
    const modifiedTd = clone.querySelector(".modified-cell");

    nameSpan.textContent = item.name;

    if (item.item_type === "folder") {
      iconImg.src = "/assets/docs/folder.svg";
      pillSpan.textContent = item.name;
      nameSpan.onclick = () =>
        fetchDocuments(path ? `${path}/${item.name}` : item.name);
    } else {
      iconImg.src = getIconUrl(item.name.split(".").pop().toLowerCase());
      pillSpan.textContent = formatFileSize(item.file_size);
      modifiedTd.textContent = formatDate(item.created_at);
    }

    checkbox.addEventListener("change", (e) => {
      if (e.target.checked) tr.classList.add("row-selected");
      else tr.classList.remove("row-selected");
    });

    tbody.appendChild(clone);
  });
}

function navigateUp() {
  if (!currentpath) return;
  const parts = currentpath.split("/");
  parts.pop();
  fetchDocuments(parts.join("/"));
}

function formatDate(isoString) {
  if (!isoString) return "--";
  const date = new Date(isoString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
