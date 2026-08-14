const TRANSLATIONS = {
  et: {
    title: "Canon LiDE 400",
    scanButton: "Skanni",
    labelResolution: "Eraldusvõime",
    labelMode: "Režiim",
    labelFormat: "Formaat",
    modeColor: "Värviline",
    modeGrayscale: "Halltoon",
    previewHeading: "Eelvaade",
    previewEmpty: "Skaneeringut veel pole.",
    historyHeading: "Viimased skaneeringud",
    historyEmpty: "Skaneeringuid veel pole.",
    scanning: "Skaneerin… kõrge eraldusvõime korral võib see võtta paar minutit.",
    scanSaved: "Skaneering salvestatud: ",
    viewing: "Vaatan: ",
    errorPrefix: "Viga: ",
    download: "Laadi alla ",
    errScanInProgress: "Skaneerimine juba käib.",
    errScannerNotFound: "Skannerit ei leitud või skaneerimine ebaõnnestus: ",
    errTimeoutPrefix: "Skaneerimine aegus ",
    errTimeoutSuffix: " sekundi järel.",
  },
  en: {
    title: "Canon LiDE 400",
    scanButton: "Scan",
    labelResolution: "Resolution",
    labelMode: "Mode",
    labelFormat: "Format",
    modeColor: "Color",
    modeGrayscale: "Grayscale",
    previewHeading: "Preview",
    previewEmpty: "No scan yet.",
    historyHeading: "Recent scans",
    historyEmpty: "No scans yet.",
    scanning: "Scanning… this can take a few minutes at high resolution.",
    scanSaved: "Scan saved: ",
    viewing: "Viewing: ",
    errorPrefix: "Error: ",
    download: "Download ",
    errScanInProgress: "Scan already in progress.",
    errScannerNotFound: "Scanner not found or scan failed: ",
    errTimeoutPrefix: "Scan timed out after ",
    errTimeoutSuffix: " seconds.",
  },
};

const LANG_STORAGE_KEY = "scanner-lang";
const DEFAULT_LANG = "et";

function getLang() {
  const stored = localStorage.getItem(LANG_STORAGE_KEY);
  return stored === "en" || stored === "et" ? stored : DEFAULT_LANG;
}

function setLang(lang) {
  localStorage.setItem(LANG_STORAGE_KEY, lang);
  applyLanguage(lang);
}

function t(key) {
  return TRANSLATIONS[getLang()][key];
}

// Translate the known, fixed backend error messages (scan.py's own JSON
// errors). Anything else (e.g. raw scanimage stderr) is left as-is - it's
// a rare technical edge case, not worth a full message-parsing layer.
function translateError(raw) {
  const lang = getLang();
  const dict = TRANSLATIONS[lang];

  if (raw === "Scan already in progress.") {
    return dict.errScanInProgress;
  }

  const notFoundPrefix = "Scanner not found or scan failed: ";
  if (raw.startsWith(notFoundPrefix)) {
    return dict.errScannerNotFound + raw.slice(notFoundPrefix.length);
  }

  const timeoutMatch = raw.match(/^Scan timed out after (\d+)s\.$/);
  if (timeoutMatch) {
    return dict.errTimeoutPrefix + timeoutMatch[1] + dict.errTimeoutSuffix;
  }

  return raw;
}

function applyLanguage(lang) {
  document.documentElement.lang = lang;
  document.title = TRANSLATIONS[lang].title;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    el.textContent = TRANSLATIONS[lang][key];
  });

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyLanguage(getLang());

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => setLang(btn.dataset.lang));
  });
});
