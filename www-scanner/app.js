const form = document.getElementById("scan-form");
const scanButton = document.getElementById("scan-button");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const downloadAreaEl = document.getElementById("download-area");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  scanButton.disabled = true;
  statusEl.textContent = "Scanning… this can take a few minutes at high resolution.";
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
      statusEl.textContent = "Error: " + result.error;
      return;
    }

    statusEl.textContent = "Scan saved: " + result.file;

    const format = form.elements["format"].value;
    if (format === "PDF") {
      previewEl.innerHTML = '<iframe src="' + result.url + '"></iframe>';
    } else {
      previewEl.innerHTML = '<img src="' + result.url + '" alt="Scan preview">';
    }

    downloadAreaEl.innerHTML =
      '<a href="' + result.url + '" download="' + result.file + '">Download ' + result.file + "</a>";
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  } finally {
    scanButton.disabled = false;
  }
});
