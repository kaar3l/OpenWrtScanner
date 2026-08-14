const form = document.getElementById("scan-form");
const scanButton = document.getElementById("scan-button");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const downloadAreaEl = document.getElementById("download-area");
const historyGridEl = document.getElementById("history-grid");
const progressWrapEl = document.getElementById("progress-wrap");
const progressBarEl = document.getElementById("progress-bar");
const progressPercentEl = document.getElementById("progress-percent");
const cancelButton = document.getElementById("cancel-button");

let currentPreviewFile = null;
let progressTimer = null;

function renderPreview(url, format, file) {
  currentPreviewFile = file;
  previewEl.innerHTML =
    format === "pdf"
      ? '<iframe src="' + url + '"></iframe>'
      : '<img src="' + url + '" alt="Scan preview">';

  downloadAreaEl.innerHTML =
    '<a href="' + url + '" download="' + file + '">' + t("download") + file + "</a>";
}

function clearPreview() {
  currentPreviewFile = null;
  previewEl.innerHTML =
    '<p class="preview-placeholder" data-i18n="previewEmpty">' + t("previewEmpty") + "</p>";
  downloadAreaEl.innerHTML = "";
}

function showProgress(percent) {
  progressWrapEl.hidden = false;
  progressBarEl.style.width = percent + "%";
  progressPercentEl.textContent = Math.round(percent) + "%";
}

function hideProgress() {
  progressWrapEl.hidden = true;
}

function stopProgressPolling() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

function startProgressPolling() {
  stopProgressPolling();
  showProgress(0);
  progressTimer = setInterval(async () => {
    try {
      const response = await fetch("/cgi-bin/progress.py");
      const data = await response.json();
      if (data.status === "running") {
        showProgress(data.percent || 0);
      }
    } catch (err) {
      // ignore transient poll failures, keep trying until the scan settles
    }
  }, 700);
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
    const tile = document.createElement("div");
    tile.className = "history-tile";
    tile.innerHTML =
      '<div class="history-thumb-wrap">' +
      '<button type="button" class="history-thumb" aria-label="' + entry.file + '">' +
      '<img src="' + entry.thumb_url + '" alt="' + entry.file + '" loading="lazy">' +
      "</button>" +
      '<button type="button" class="history-delete" aria-label="' + t("deleteButton") + '">✕</button>' +
      "</div>" +
      '<span class="history-caption">' + entry.timestamp + "</span>";

    const img = tile.querySelector("img");
    img.addEventListener("error", () => {
      img.replaceWith(Object.assign(document.createElement("span"), {
        className: "doc-icon",
        textContent: "\u{1F4C4}",
      }));
    });

    tile.querySelector(".history-thumb").addEventListener("click", () => {
      renderPreview(entry.url, entry.format, entry.file);
      statusEl.classList.remove("error");
      statusEl.textContent = t("viewing") + entry.file;
    });

    tile.querySelector(".history-delete").addEventListener("click", async (event) => {
      event.stopPropagation();
      if (!window.confirm(t("confirmDelete"))) {
        return;
      }
      try {
        await fetch("/cgi-bin/delete.py?name=" + encodeURIComponent(entry.file), {
          method: "DELETE",
        });
      } catch (err) {
        // best-effort; loadHistory() below reflects whatever actually happened
      }
      if (currentPreviewFile === entry.file) {
        clearPreview();
      }
      loadHistory();
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
  startProgressPolling();

  const formData = new URLSearchParams(new FormData(form));

  try {
    const response = await fetch("/cgi-bin/scan.py", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    const result = await response.json();

    if (!result.ok) {
      if (result.cancelled) {
        statusEl.classList.remove("error");
        statusEl.textContent = t("scanCancelled");
      } else {
        statusEl.classList.add("error");
        statusEl.textContent = t("errorPrefix") + translateError(result.error);
      }
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
    stopProgressPolling();
    hideProgress();
    scanButton.disabled = false;
    cancelButton.disabled = false;
  }
});

cancelButton.addEventListener("click", async () => {
  cancelButton.disabled = true;
  try {
    await fetch("/cgi-bin/cancel.py", { method: "POST" });
  } catch (err) {
    // best-effort; the scan.py fetch above will resolve either way and
    // report whatever actually happened
  }
});

loadHistory();
