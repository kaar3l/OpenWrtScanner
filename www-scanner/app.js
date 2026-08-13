const form = document.getElementById("scan-form");
const scanButton = document.getElementById("scan-button");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const downloadAreaEl = document.getElementById("download-area");
const historyGridEl = document.getElementById("history-grid");

function renderPreview(url, format, file) {
  previewEl.innerHTML =
    format === "pdf"
      ? '<iframe src="' + url + '"></iframe>'
      : '<img src="' + url + '" alt="Scan preview">';

  downloadAreaEl.innerHTML =
    '<a href="' + url + '" download="' + file + '">' + t("download") + file + "</a>";
}

async function loadHistory() {
  let entries;
  try {
    const response = await fetch("/cgi-bin/history.py");
    entries = await response.json();
  } catch (err) {
    return; // history is a nice-to-have; a failed fetch shouldn't break the page
  }

  if (!entries.length) {
    historyGridEl.innerHTML =
      '<p class="history-empty" data-i18n="historyEmpty">' + t("historyEmpty") + "</p>";
    return;
  }

  historyGridEl.innerHTML = "";
  for (const entry of entries) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "history-tile";
    tile.innerHTML =
      '<div class="history-thumb">' +
      (entry.is_image
        ? '<img src="' + entry.url + '" alt="' + entry.file + '" loading="lazy">'
        : '<span class="doc-icon">\u{1F4C4}</span>') +
      "</div>" +
      '<span class="history-caption">' + entry.timestamp + "</span>";
    tile.addEventListener("click", () => {
      renderPreview(entry.url, entry.format, entry.file);
      statusEl.classList.remove("error");
      statusEl.textContent = t("viewing") + entry.file;
    });
    historyGridEl.appendChild(tile);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  scanButton.disabled = true;
  statusEl.classList.remove("error");
  statusEl.textContent = t("scanning");
  previewEl.innerHTML = "";
  downloadAreaEl.innerHTML = "";

  const formData = new URLSearchParams(new FormData(form));

  try {
    const response = await fetch("/cgi-bin/scan.py", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    const result = await response.json();

    if (!result.ok) {
      statusEl.classList.add("error");
      statusEl.textContent = t("errorPrefix") + translateError(result.error);
      return;
    }

    statusEl.textContent = t("scanSaved") + result.file;

    const format = form.elements["format"].value.toLowerCase();
    renderPreview(result.url, format, result.file);
    loadHistory();
  } catch (err) {
    statusEl.classList.add("error");
    statusEl.textContent = t("errorPrefix") + err.message;
  } finally {
    scanButton.disabled = false;
  }
});

loadHistory();
