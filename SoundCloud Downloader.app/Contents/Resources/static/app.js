// SoundCloud Downloader Web App Client Logic

let currentMediaInfo = null;
let selectedQuality = "direct_stream";
let playlistFormat = "zip"; // "zip" or "folder"
let activeTaskId = null;
let pollInterval = null;
let customOutputDir = null;
let availableQualities = {};

// DOM Elements
const systemStatus = document.getElementById("systemStatus");
const statusText = document.getElementById("statusText");
const statusDot = systemStatus.querySelector(".status-dot");
const currentFolderLabel = document.getElementById("currentFolderLabel");
const folderBtn = document.getElementById("folderBtn");
const historyBtn = document.getElementById("historyBtn");
const historyBadge = document.getElementById("historyBadge");

const urlInput = document.getElementById("urlInput");
const pasteBtn = document.getElementById("pasteBtn");
const clearBtn = document.getElementById("clearBtn");
const fetchBtn = document.getElementById("fetchBtn");
const fetchSpinner = document.getElementById("fetchSpinner");
const btnText = fetchBtn.querySelector(".btn-text");

const errorBanner = document.getElementById("errorBanner");
const errorMessage = document.getElementById("errorMessage");
const errorCloseBtn = document.getElementById("errorCloseBtn");

const resultSection = document.getElementById("resultSection");
const trackView = document.getElementById("trackView");
const playlistView = document.getElementById("playlistView");

// Single Track Elements
const trackArtwork = document.getElementById("trackArtwork");
const trackGlow = document.getElementById("trackGlow");
const trackArtist = document.getElementById("trackArtist");
const trackTitle = document.getElementById("trackTitle");
const trackDuration = document.getElementById("trackDuration");
const trackGenre = document.getElementById("trackGenre");
const trackSourceBar = document.getElementById("trackSourceBar");
const trackSourceValue = document.getElementById("trackSourceValue");
const trackSourceSub = document.getElementById("trackSourceSub");
const trackQualityNotice = document.getElementById("trackQualityNotice");
const trackQualityNoticeText = document.getElementById("trackQualityNoticeText");
const trackQualityGrid = document.getElementById("trackQualityGrid");
const downloadTrackBtn = document.getElementById("downloadTrackBtn");
const downloadTrackBtnText = document.getElementById("downloadTrackBtnText");
const trackEmbedArtwork = document.getElementById("trackEmbedArtwork");
const trackEmbedMetadata = document.getElementById("trackEmbedMetadata");
const trackNormalizeQuiet = document.getElementById("trackNormalizeQuiet");
const trackPlayBtn = document.getElementById("trackPlayBtn");

// Floating Audio Mini-Player Elements
const audioMiniPlayer = document.getElementById("audioMiniPlayer");
const previewAudio = document.getElementById("previewAudio");
const playerThumb = document.getElementById("playerThumb");
const playerWaveIndicator = document.getElementById("playerWaveIndicator");
const playerTitle = document.getElementById("playerTitle");
const playerArtist = document.getElementById("playerArtist");
const playerPlayPauseBtn = document.getElementById("playerPlayPauseBtn");
const playerLoadingSpinner = document.getElementById("playerLoadingSpinner");
const playerPlayIcon = document.getElementById("playerPlayIcon");
const playerPauseIcon = document.getElementById("playerPauseIcon");
const playerCurrentTime = document.getElementById("playerCurrentTime");
const playerTotalTime = document.getElementById("playerTotalTime");
const playerSeekBar = document.getElementById("playerSeekBar");
const playerSeekProgress = document.getElementById("playerSeekProgress");
const playerVolumeBtn = document.getElementById("playerVolumeBtn");
const volumeIcon = document.getElementById("volumeIcon");
const muteIcon = document.getElementById("muteIcon");
const playerVolumeSlider = document.getElementById("playerVolumeSlider");
const playerCloseBtn = document.getElementById("playerCloseBtn");

let currentPlayingUrl = null;
let currentPlayingIndex = null;
let isSeekingAudio = false;
let lastVolume = 0.8;

// Playlist Elements
const playlistArtwork = document.getElementById("playlistArtwork");
const playlistGlow = document.getElementById("playlistGlow");
const playlistArtist = document.getElementById("playlistArtist");
const playlistTitle = document.getElementById("playlistTitle");
const playlistTrackCount = document.getElementById("playlistTrackCount");
const playlistDuration = document.getElementById("playlistDuration");
const playlistTypeBadge = document.getElementById("playlistTypeBadge");
const playlistSourceBar = document.getElementById("playlistSourceBar");
const playlistSourceValue = document.getElementById("playlistSourceValue");
const playlistQualityNotice = document.getElementById("playlistQualityNotice");
const playlistQualityNoticeText = document.getElementById("playlistQualityNoticeText");
const playlistQualityGrid = document.getElementById("playlistQualityGrid");
const playlistNormalizeQuiet = document.getElementById("playlistNormalizeQuiet");
const choiceZip = document.getElementById("choiceZip");
const choiceFolder = document.getElementById("choiceFolder");
const tracklistItems = document.getElementById("tracklistItems");
const selectAllCheckbox = document.getElementById("selectAllCheckbox");
const selectionStatus = document.getElementById("selectionStatus");
const selectNoneBtn = document.getElementById("selectNoneBtn");
const downloadPlaylistBtn = document.getElementById("downloadPlaylistBtn");
const downloadPlaylistBtnText = document.getElementById("downloadPlaylistBtnText");

// Clipboard Smart Toast Elements
const clipboardToast = document.getElementById("clipboardToast");
const toastUrlText = document.getElementById("toastUrlText");
const toastLoadBtn = document.getElementById("toastLoadBtn");
const toastDismissBtn = document.getElementById("toastDismissBtn");

// Progress Modal
const progressModal = document.getElementById("progressModal");
const progressModalTitle = document.getElementById("progressModalTitle");
const progressModalSubtitle = document.getElementById("progressModalSubtitle");
const progressBarFill = document.getElementById("progressBarFill");
const progressPercent = document.getElementById("progressPercent");
const progressSpeed = document.getElementById("progressSpeed");
const progressEta = document.getElementById("progressEta");
const progressCurrentDetail = document.getElementById("progressCurrentDetail");
const cancelDownloadBtn = document.getElementById("cancelDownloadBtn");

// Success Modal
const successModal = document.getElementById("successModal");
const successFileName = document.getElementById("successFileName");
const successFileSize = document.getElementById("successFileSize");
const successFilePath = document.getElementById("successFilePath");
const revealFinderBtn = document.getElementById("revealFinderBtn");
const browserDownloadLink = document.getElementById("browserDownloadLink");
const closeSuccessBtn = document.getElementById("closeSuccessBtn");

// History Modal
const historyModal = document.getElementById("historyModal");
const historyListContainer = document.getElementById("historyListContainer");
const emptyHistoryMsg = document.getElementById("emptyHistoryMsg");
const closeHistoryBtn = document.getElementById("closeHistoryBtn");

let lastCompletedResultPath = "";

// Initialize System Status
async function initSystem() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("Status check failed");
    const data = await res.json();
    
    availableQualities = data.qualities || {};
    customOutputDir = data.default_output_dir;
    
    if (data.ffmpeg_ready) {
      statusDot.classList.add("ready");
      statusText.textContent = "FFmpeg активен • Готов к загрузке";
    } else {
      statusText.textContent = "Базовый режим (без FFmpeg)";
    }

    if (customOutputDir) {
      const parts = customOutputDir.split("/");
      currentFolderLabel.textContent = parts[parts.length - 1] || "Загрузки";
      currentFolderLabel.title = customOutputDir;
    }

    updateHistoryBadge();
  } catch (err) {
    statusText.textContent = "Ошибка подключения к серверу";
    console.error(err);
  }
}

// Choose Folder via macOS Dialog
folderBtn.addEventListener("click", async () => {
  try {
    folderBtn.style.opacity = "0.7";
    const res = await fetch("/api/choose_directory", { method: "POST" });
    const data = await res.json();
    if (data.path) {
      customOutputDir = data.path;
      const parts = customOutputDir.split("/");
      currentFolderLabel.textContent = parts[parts.length - 1] || "Выбранная папка";
      currentFolderLabel.title = customOutputDir;
    }
  } catch (err) {
    showError("Не удалось открыть выбор папки: " + err.message);
  } finally {
    folderBtn.style.opacity = "1";
  }
});

// Input controls
urlInput.addEventListener("input", () => {
  clearBtn.style.display = urlInput.value ? "flex" : "none";
});

clearBtn.addEventListener("click", () => {
  urlInput.value = "";
  clearBtn.style.display = "none";
  urlInput.focus();
});

pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text.trim();
      clearBtn.style.display = "flex";
      if (text.includes("soundcloud.com")) {
        fetchMediaInfo();
      }
    }
  } catch (err) {
    urlInput.focus();
  }
});

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    fetchMediaInfo();
  }
});

fetchBtn.addEventListener("click", fetchMediaInfo);

errorCloseBtn.addEventListener("click", () => {
  errorBanner.style.display = "none";
});

function showError(msg) {
  errorMessage.textContent = msg;
  errorBanner.style.display = "flex";
}

function hideError() {
  errorBanner.style.display = "none";
}

// Fetch Media Info from Backend
async function fetchMediaInfo() {
  const url = urlInput.value.trim();
  if (!url) {
    showError("Пожалуйста, вставьте ссылку на SoundCloud");
    return;
  }
  if (!url.includes("soundcloud.com")) {
    showError("Ссылка должна быть с soundcloud.com");
    return;
  }

  hideError();
  btnText.style.display = "none";
  fetchSpinner.style.display = "block";
  fetchBtn.disabled = true;

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Не удалось загрузить данные трека");
    }

    currentMediaInfo = data;
    renderMediaInfo(data);
  } catch (err) {
    showError(err.message);
    resultSection.style.display = "none";
  } finally {
    btnText.style.display = "block";
    fetchSpinner.style.display = "none";
    fetchBtn.disabled = false;
  }
}

// Render Retrieved Info
function renderMediaInfo(info) {
  resultSection.style.display = "block";

  const qMap = info.qualities || {};
  const qKeys = Object.keys(qMap);
  if (!qMap[selectedQuality]) {
    selectedQuality = qKeys.includes("direct_stream") ? "direct_stream" : (qKeys[0] || "direct_stream");
  }

  if (info.is_playlist) {
    trackView.style.display = "none";
    playlistView.style.display = "flex";
    renderPlaylistView(info);
  } else {
    playlistView.style.display = "none";
    trackView.style.display = "flex";
    renderTrackView(info);
  }

  resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Calculate estimated file size in bytes based on true stream bitrates
function calculateEstimatedSizeBytes(qualityKey, durationSeconds, trackCount = 1, sourceBitrate = 160) {
  if (!durationSeconds || durationSeconds <= 0) return 0;

  let br = 160;
  const qItem = (currentMediaInfo?.qualities && currentMediaInfo.qualities[qualityKey]) || (availableQualities && availableQualities[qualityKey]);

  if (qItem && qItem.bitrate) {
    br = qItem.bitrate;
  } else if (qualityKey === "direct_stream") {
    br = sourceBitrate > 0 ? sourceBitrate : 160;
  } else if (qualityKey === "mp3_128") {
    br = 128;
  } else if (qualityKey === "mp3_source" || qualityKey === "mp3_160") {
    br = Math.min(sourceBitrate || 160, 160);
  } else if (qualityKey === "mp3_256" || qualityKey === "m4a_256") {
    br = 256;
  } else if (qualityKey === "mp3_320") {
    br = 320;
  } else if (qualityKey === "flac") {
    br = 850;
  } else if (qualityKey === "wav") {
    br = 1411;
  }

  // Exact audio stream data: (bitrate kbps * 1000 / 8) * duration seconds
  const audioBytes = (br * 1000 / 8) * durationSeconds;

  // Real ID3/artwork metadata overhead: approx 35 KB per track (realistic)
  const overhead = 35 * 1024 * Math.max(1, trackCount);

  return Math.round(audioBytes + overhead);
}

// Format bytes into human-readable Russian string (e.g. "8.4 МБ", "118 МБ", "1.2 ГБ")
function formatEstimatedSize(bytes) {
  if (!bytes || isNaN(bytes) || bytes <= 0) return "";
  const mb = bytes / (1024 * 1024);
  if (mb < 1) {
    if (mb < 0.1) {
      return `${Math.round(bytes / 1024)} КБ`;
    }
    return `${mb.toFixed(1)} МБ`;
  }
  if (mb >= 1000) {
    const gb = mb / 1024;
    return `${gb.toFixed(1)} ГБ`;
  }
  if (mb >= 100) {
    return `${Math.round(mb)} МБ`;
  }
  return `${mb.toFixed(1)} МБ`;
}

// Calculate the total duration in seconds of currently selected playlist tracks
function getSelectedTracksDuration() {
  if (!currentMediaInfo || !currentMediaInfo.tracks) {
    return currentMediaInfo?.total_duration || 0;
  }
  const cbs = document.querySelectorAll(".track-select-cb");
  if (cbs.length === 0) {
    if (currentMediaInfo.total_duration) return currentMediaInfo.total_duration;
    return currentMediaInfo.tracks.reduce((acc, t) => acc + (parseFloat(t.duration) || 0), 0);
  }
  const selectedSet = new Set(getSelectedTrackIndices());
  let totalDur = 0;
  let countWithDuration = 0;
  currentMediaInfo.tracks.forEach(t => {
    if (selectedSet.has(t.index)) {
      if (t.duration && !isNaN(t.duration)) {
        totalDur += parseFloat(t.duration);
        countWithDuration++;
      }
    }
  });
  if (countWithDuration < selectedSet.size && currentMediaInfo.total_duration) {
    const avg = currentMediaInfo.total_duration / Math.max(1, currentMediaInfo.track_count || currentMediaInfo.tracks.length);
    const missing = selectedSet.size - countWithDuration;
    totalDur += (avg * missing);
  }
  return totalDur;
}

function renderTrackView(info) {
  const artwork = info.artwork || "https://a-v2.sndcdn.com/assets/images/default/avatar-f000000000.png";
  trackArtwork.src = artwork;
  trackGlow.style.backgroundImage = `url('${artwork}')`;

  trackArtist.textContent = info.uploader || "SoundCloud Артист";
  trackTitle.textContent = info.title || "SoundCloud Трек";
  trackDuration.textContent = info.duration_formatted || "--:--";
  trackGenre.textContent = info.genre || "SoundCloud";

  // Display Source Stream Quality Info
  if (info.source_info) {
    trackSourceValue.textContent = info.source_info.label || "160 kbps (HQ)";
    if (info.source_info.has_original) {
      trackSourceValue.textContent = "Оригинальный файл от автора (Studio / Lossless)";
      trackSourceSub.textContent = "Доступен оригинальный несжатый файл от автора!";
    } else {
      trackSourceSub.textContent = `Максимально доступное качество аудио на серверах SoundCloud (${info.source_info.codec} ${info.source_info.bitrate} kbps)`;
    }
  }

  renderQualityGrid(trackQualityGrid, info.qualities || availableQualities, (q) => {
    selectedQuality = q;
    updateTrackButtonText();
  }, false);

  if (trackPlayBtn) {
    trackPlayBtn.onclick = (e) => {
      e.stopPropagation();
      playTrackPreview({
        url: info.url,
        title: info.title,
        uploader: info.uploader,
        artwork: artwork,
        duration: info.duration,
        index: null
      });
    };
  }

  updateTrackButtonText();
}

function updateTrackButtonText() {
  const qLabel = (availableQualities[selectedQuality]?.label || "MP3 320").split("(")[0].trim();
  const dur = currentMediaInfo?.duration || 0;
  const srcBitrate = currentMediaInfo?.source_info?.bitrate || 160;
  let sizeSuffix = "";
  if (dur > 0) {
    const bytes = calculateEstimatedSizeBytes(selectedQuality, dur, 1, srcBitrate);
    const sizeStr = formatEstimatedSize(bytes);
    if (sizeStr) {
      sizeSuffix = ` • ~${sizeStr}`;
    }
  }
  downloadTrackBtnText.textContent = `Скачать трек (${qLabel}${sizeSuffix})`;
}

function renderPlaylistView(info) {
  const artwork = info.artwork || "https://a-v2.sndcdn.com/assets/images/default/avatar-f000000000.png";
  playlistArtwork.src = artwork;
  playlistGlow.style.backgroundImage = `url('${artwork}')`;

  playlistArtist.textContent = info.uploader || "SoundCloud Артист";
  playlistTitle.textContent = info.title || "SoundCloud Плейлист";
  playlistTrackCount.textContent = `${info.track_count} треков`;
  playlistDuration.textContent = info.total_duration_formatted ? `~${info.total_duration_formatted}` : "";
  playlistTypeBadge.textContent = info.type === "album" ? "Альбом" : "Плейлист";

  // Display Source Info
  if (info.source_info) {
    playlistSourceValue.textContent = info.source_info.label || "Стриминг 160 kbps";
  }

  // Render Track List FIRST so DOM elements and checkboxes are ready
  tracklistItems.innerHTML = "";
  const tracks = info.tracks || [];

  tracks.forEach((t) => {
    const row = document.createElement("div");
    row.className = "track-row";
    row.dataset.index = t.index;
    row.dataset.url = t.url;
    if (currentPlayingIndex === t.index && !previewAudio.paused) {
      row.classList.add("is-playing");
    }

    row.innerHTML = `
      <label class="custom-checkbox">
        <input type="checkbox" class="track-select-cb" data-index="${t.index}" checked>
        <span class="checkmark"></span>
      </label>
      <button class="track-play-inline-btn" title="Слушать превью" data-index="${t.index}">
        <svg class="play-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="6 3 20 12 6 21 6 3"></polygon>
        </svg>
        <svg class="pause-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="display: none;">
          <rect x="6" y="4" width="4" height="16"></rect>
          <rect x="14" y="4" width="4" height="16"></rect>
        </svg>
      </button>
      <span class="track-num">${t.index}</span>
      <div class="track-row-info">
        <span class="track-row-title" title="${t.title}">${t.title}</span>
        <span class="track-row-artist">${t.uploader}</span>
      </div>
      <span class="track-row-dur">${t.duration_formatted}</span>
    `;

    // Double-click row to preview
    row.addEventListener("dblclick", (e) => {
      if (e.target.closest(".custom-checkbox")) return;
      playTrackPreview({
        url: t.url,
        title: t.title,
        uploader: t.uploader,
        artwork: t.artwork || artwork,
        duration: t.duration,
        duration_formatted: t.duration_formatted,
        index: t.index
      });
    });

    // Inline play button click
    const inlineBtn = row.querySelector(".track-play-inline-btn");
    inlineBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      playTrackPreview({
        url: t.url,
        title: t.title,
        uploader: t.uploader,
        artwork: t.artwork || artwork,
        duration: t.duration,
        duration_formatted: t.duration_formatted,
        index: t.index
      });
    });

    // Checkbox container stopPropagation to prevent accidental double-click / preview triggers
    const cb = row.querySelector(".custom-checkbox");
    cb.addEventListener("click", (e) => {
      e.stopPropagation();
    });

    tracklistItems.appendChild(row);
  });

  // Checkbox interactions
  setupTrackSelectionListeners();
  updateSelectionCount();

  // Render Quality Grid with estimated sizes calculated for all selected tracks
  renderQualityGrid(playlistQualityGrid, info.qualities || availableQualities, (q) => {
    selectedQuality = q;
    updatePlaylistButtonText();
  }, true);

  updatePlaylistButtonText();
}

function renderQualityGrid(container, qualities, onSelect, isPlaylist = false) {
  container.innerHTML = "";

  let duration = 0;
  let trackCount = 1;
  const srcBitrate = currentMediaInfo?.source_info?.bitrate || 160;

  if (isPlaylist) {
    trackCount = getSelectedTrackIndices().length;
    duration = getSelectedTracksDuration();
  } else {
    duration = currentMediaInfo?.duration || 0;
    trackCount = 1;
  }

  Object.keys(qualities).forEach((key) => {
    const item = qualities[key];
    const card = document.createElement("div");
    card.className = `quality-option-card ${key === selectedQuality ? "selected" : ""}`;
    card.dataset.quality = key;
    
    const badgeHtml = item.badge ? `<span class="q-badge">${item.badge}</span>` : "";

    let sizeTagHtml = "";
    if (duration > 0 && trackCount > 0) {
      const bytes = calculateEstimatedSizeBytes(key, duration, trackCount, srcBitrate);
      const sizeStr = formatEstimatedSize(bytes);
      if (sizeStr) {
        sizeTagHtml = `<span class="q-size-tag" data-qsize="${key}">~${sizeStr}</span>`;
      }
    }

    card.innerHTML = `
      <div class="q-label-box">
        <div class="q-title-row">
          <span class="q-title">${item.label.split("(")[0].trim()}</span>
          ${sizeTagHtml}
          ${badgeHtml}
        </div>
        <div class="q-sub">${item.sublabel || (item.label.includes("(") ? "(" + item.label.split("(")[1] : item.ext.toUpperCase())}</div>
      </div>
      <div class="q-check-dot"></div>
    `;

    card.addEventListener("click", () => {
      container.querySelectorAll(".quality-option-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      onSelect(key);
      updateQualityNotice(key, isPlaylist);
    });

    container.appendChild(card);
  });
  updateQualityNotice(selectedQuality, isPlaylist);
}

function updateQualityCardSizes(container, isPlaylist = false) {
  if (!container || !currentMediaInfo) return;
  let duration = 0;
  let trackCount = 1;
  const srcBitrate = currentMediaInfo?.source_info?.bitrate || 160;

  if (isPlaylist) {
    trackCount = getSelectedTrackIndices().length;
    duration = getSelectedTracksDuration();
  } else {
    duration = currentMediaInfo?.duration || 0;
    trackCount = 1;
  }

  const cards = container.querySelectorAll(".quality-option-card");
  cards.forEach(card => {
    const qKey = card.dataset.quality;
    if (!qKey) return;
    let sizeTag = card.querySelector(".q-size-tag");

    if (duration > 0 && trackCount > 0) {
      const bytes = calculateEstimatedSizeBytes(qKey, duration, trackCount, srcBitrate);
      const sizeStr = formatEstimatedSize(bytes);
      if (sizeTag) {
        sizeTag.textContent = `~${sizeStr}`;
        sizeTag.style.display = "";
      } else {
        const titleRow = card.querySelector(".q-title-row");
        if (titleRow) {
          const newTag = document.createElement("span");
          newTag.className = "q-size-tag";
          newTag.dataset.qsize = qKey;
          newTag.textContent = `~${sizeStr}`;
          const badge = titleRow.querySelector(".q-badge");
          if (badge) {
            titleRow.insertBefore(newTag, badge);
          } else {
            titleRow.appendChild(newTag);
          }
        }
      }
    } else if (sizeTag) {
      sizeTag.style.display = "none";
    }
  });
}

function updateQualityNotice(qualityKey, isPlaylist = false) {
  const noticeBox = isPlaylist ? playlistQualityNotice : trackQualityNotice;
  const noticeText = isPlaylist ? playlistQualityNoticeText : trackQualityNoticeText;
  if (!noticeBox || !noticeText) return;

  const src = currentMediaInfo?.source_info;
  const srcLabel = src?.label || "160 kbps (AAC)";

  if (qualityKey === "direct_stream") {
    noticeText.textContent = `⚡ Прямое сохранение исходного потока (${srcLabel}) 1:1 без пережатия. Нулевая потеря качества и моментальная загрузка!`;
    noticeBox.style.display = "flex";
  } else if (qualityKey === "mp3_source") {
    noticeText.textContent = `🎵 Преобразование в универсальный формат MP3 с сохранением битрейта источника (${srcLabel}) для гарантированной совместимости с любыми плеерами.`;
    noticeBox.style.display = "flex";
  } else if (qualityKey === "flac") {
    noticeText.textContent = `💎 Студийный оригинал автора в несжатом Lossless FLAC.`;
    noticeBox.style.display = "flex";
  } else if (qualityKey === "wav") {
    noticeText.textContent = `🔊 Студийный 16-bit PCM звук. Обратите внимание: WAV-контейнер не поддерживает встроенные ID3-обложки.`;
    noticeBox.style.display = "flex";
  } else if (qualityKey === "mp3_128") {
    noticeText.textContent = `📦 Стандартный битрейт MP3 128 kbps с минимальным размером файла.`;
    noticeBox.style.display = "flex";
  } else {
    noticeBox.style.display = "none";
  }

  if (!isPlaylist && trackEmbedArtwork) {
    if (qualityKey === "wav") {
      trackEmbedArtwork.checked = false;
      trackEmbedArtwork.disabled = true;
    } else {
      trackEmbedArtwork.disabled = false;
      trackEmbedArtwork.checked = true;
    }
  }
}

// Playlist Format selection (ZIP vs Folder)
choiceZip.addEventListener("click", () => {
  playlistFormat = "zip";
  choiceZip.classList.add("active");
  choiceFolder.classList.remove("active");
  updatePlaylistButtonText();
});

choiceFolder.addEventListener("click", () => {
  playlistFormat = "folder";
  choiceFolder.classList.add("active");
  choiceZip.classList.remove("active");
  updatePlaylistButtonText();
});

function setupTrackSelectionListeners() {
  const cbs = document.querySelectorAll(".track-select-cb");
  cbs.forEach(cb => {
    cb.addEventListener("change", () => {
      updateSelectionCount();
      updatePlaylistButtonText();
      updateQualityCardSizes(playlistQualityGrid, true);
    });
  });

  selectAllCheckbox.addEventListener("change", () => {
    const isChecked = selectAllCheckbox.checked;
    cbs.forEach(cb => cb.checked = isChecked);
    updateSelectionCount();
    updatePlaylistButtonText();
    updateQualityCardSizes(playlistQualityGrid, true);
  });

  selectNoneBtn.addEventListener("click", () => {
    cbs.forEach(cb => cb.checked = false);
    selectAllCheckbox.checked = false;
    updateSelectionCount();
    updatePlaylistButtonText();
    updateQualityCardSizes(playlistQualityGrid, true);
  });
}

function getSelectedTrackIndices() {
  const cbs = document.querySelectorAll(".track-select-cb");
  if (cbs.length === 0 && currentMediaInfo?.tracks) {
    return currentMediaInfo.tracks.map(t => t.index);
  }
  const checkedCbs = document.querySelectorAll(".track-select-cb:checked");
  return Array.from(checkedCbs).map(cb => parseInt(cb.dataset.index));
}

function updateSelectionCount() {
  const total = currentMediaInfo?.tracks?.length || 0;
  const selected = getSelectedTrackIndices().length;
  selectionStatus.textContent = `Выбрано: ${selected} из ${total}`;
  selectAllCheckbox.checked = selected === total && total > 0;
}

function updatePlaylistButtonText() {
  const selected = getSelectedTrackIndices().length;
  const qLabel = (availableQualities[selectedQuality]?.label || "MP3 320").split("(")[0].trim();
  const dur = getSelectedTracksDuration();
  const srcBitrate = currentMediaInfo?.source_info?.bitrate || 160;

  let sizeSuffix = "";
  if (dur > 0 && selected > 0) {
    const bytes = calculateEstimatedSizeBytes(selectedQuality, dur, selected, srcBitrate);
    const sizeStr = formatEstimatedSize(bytes);
    if (sizeStr) {
      sizeSuffix = ` • ~${sizeStr}`;
    }
  }

  if (playlistFormat === "zip") {
    downloadPlaylistBtnText.textContent = `Скачать ZIP-архив (${selected} треков, ${qLabel}${sizeSuffix})`;
  } else {
    downloadPlaylistBtnText.textContent = `Скачать в папку (${selected} треков, ${qLabel}${sizeSuffix})`;
  }

  downloadPlaylistBtn.disabled = selected === 0;
  downloadPlaylistBtn.style.opacity = selected === 0 ? "0.5" : "1";
}

// Download Triggering
downloadTrackBtn.addEventListener("click", () => {
  if (!currentMediaInfo) return;
  startDownload({
    url: currentMediaInfo.url,
    quality: selectedQuality,
    as_zip: false,
    output_dir: customOutputDir,
    embed_artwork: trackEmbedArtwork.checked,
    embed_metadata: trackEmbedMetadata.checked,
    normalize_quiet: trackNormalizeQuiet ? trackNormalizeQuiet.checked : true
  });
});

downloadPlaylistBtn.addEventListener("click", () => {
  if (!currentMediaInfo) return;
  const selectedTracks = getSelectedTrackIndices();
  if (selectedTracks.length === 0) {
    showError("Выберите хотя бы один трек для загрузки");
    return;
  }

  startDownload({
    url: currentMediaInfo.url,
    quality: selectedQuality,
    as_zip: playlistFormat === "zip",
    output_dir: customOutputDir,
    selected_tracks: selectedTracks,
    embed_artwork: true,
    embed_metadata: true,
    normalize_quiet: playlistNormalizeQuiet ? playlistNormalizeQuiet.checked : true
  });
});

// Download Task Execution & Polling
async function startDownload(payload) {
  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Не удалось запустить загрузку");
    }

    activeTaskId = data.task_id;
    showProgressModal();
    startPollingProgress();
  } catch (err) {
    showError(err.message);
  }
}

function showProgressModal() {
  progressModalTitle.textContent = currentMediaInfo.is_playlist ? "Скачивание плейлиста..." : "Скачивание трека...";
  progressModalSubtitle.textContent = currentMediaInfo.title;
  progressBarFill.style.width = "0%";
  progressPercent.textContent = "0%";
  progressSpeed.textContent = "";
  progressEta.textContent = "";
  progressCurrentDetail.textContent = "Подготовка к загрузке...";
  progressModal.style.display = "flex";
}

function startPollingProgress() {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    if (!activeTaskId) return;

    try {
      const res = await fetch(`/api/progress?id=${activeTaskId}`);
      if (!res.ok) return;

      const task = await res.json();

      // Update UI
      const pct = task.progress || 0;
      progressBarFill.style.width = `${pct}%`;
      progressPercent.textContent = `${Math.round(pct)}%`;
      progressSpeed.textContent = task.speed || "";
      progressEta.textContent = task.eta ? `Осталось: ${task.eta}` : "";
      progressCurrentDetail.textContent = task.message || "Скачивание...";

      if (task.status === "completed") {
        clearInterval(pollInterval);
        progressModal.style.display = "none";
        showSuccessModal(task);
        updateHistoryBadge();
      } else if (task.status === "error") {
        clearInterval(pollInterval);
        progressModal.style.display = "none";
        showError(task.error_message || "Произошла ошибка при загрузке");
      } else if (task.status === "cancelled") {
        clearInterval(pollInterval);
        progressModal.style.display = "none";
      }
    } catch (err) {
      console.error("Progress poll error:", err);
    }
  }, 500);
}

// Cancel Download
cancelDownloadBtn.addEventListener("click", async () => {
  if (activeTaskId) {
    try {
      await fetch("/api/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: activeTaskId })
      });
    } catch (err) {
      console.error(err);
    }
  }
  clearInterval(pollInterval);
  progressModal.style.display = "none";
});

// Success Modal
function showSuccessModal(task) {
  lastCompletedResultPath = task.result_path;
  successFileName.textContent = task.result_filename;
  successFileSize.textContent = task.result_filesize;
  successFilePath.textContent = task.result_path;

  // Set browser download link
  browserDownloadLink.href = `/api/file?path=${encodeURIComponent(task.result_path)}`;
  browserDownloadLink.download = task.result_filename;

  successModal.style.display = "flex";
}

revealFinderBtn.addEventListener("click", async () => {
  if (!lastCompletedResultPath) return;
  try {
    await fetch("/api/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: lastCompletedResultPath })
    });
  } catch (err) {
    console.error(err);
  }
});

closeSuccessBtn.addEventListener("click", () => {
  successModal.style.display = "none";
});

// History Drawer
historyBtn.addEventListener("click", openHistory);
closeHistoryBtn.addEventListener("click", () => {
  historyModal.style.display = "none";
});

async function openHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    const list = data.history || [];

    historyListContainer.innerHTML = "";
    if (list.length === 0) {
      emptyHistoryMsg.style.display = "block";
      historyListContainer.appendChild(emptyHistoryMsg);
    } else {
      emptyHistoryMsg.style.display = "none";
      list.forEach(item => {
        const el = document.createElement("div");
        el.className = "history-item";
        el.innerHTML = `
          <div class="history-item-info">
            <div class="item-name">${item.filename}</div>
            <div class="item-size">${item.filesize}</div>
          </div>
          <button class="history-reveal-btn" data-path="${item.result_path}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            Finder
          </button>
        `;
        el.querySelector(".history-reveal-btn").addEventListener("click", async () => {
          await fetch("/api/reveal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: item.result_path })
          });
        });
        historyListContainer.appendChild(el);
      });
    }

    historyModal.style.display = "flex";
  } catch (err) {
    console.error(err);
  }
}

async function updateHistoryBadge() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    const count = (data.history || []).length;
    if (count > 0) {
      historyBadge.textContent = count;
      historyBadge.style.display = "inline-block";
    } else {
      historyBadge.style.display = "none";
    }
  } catch (e) {}
}

// Smart Auto-Clipboard Detection
let lastDetectedClipboardUrl = "";

async function checkClipboardForSoundCloud() {
  try {
    const text = await navigator.clipboard.readText();
    if (!text) return;
    const clean = text.trim();
    if (
      clean.includes("soundcloud.com") &&
      clean !== lastDetectedClipboardUrl &&
      clean !== urlInput.value.trim()
    ) {
      lastDetectedClipboardUrl = clean;
      showClipboardToast(clean);
    }
  } catch (e) {
    // Permission or focus restriction
  }
}

function showClipboardToast(url) {
  if (!clipboardToast || !toastUrlText) return;
  let displayPath = url;
  try {
    const u = new URL(url);
    displayPath = u.pathname.replace(/^\//, '');
  } catch (e) {}

  toastUrlText.textContent = displayPath || url;
  clipboardToast.style.display = "flex";
}

function hideClipboardToast() {
  if (clipboardToast) clipboardToast.style.display = "none";
}

toastLoadBtn?.addEventListener("click", () => {
  if (lastDetectedClipboardUrl) {
    urlInput.value = lastDetectedClipboardUrl;
    clearBtn.style.display = "flex";
    hideClipboardToast();
    fetchMediaInfo();
  }
});

toastDismissBtn?.addEventListener("click", () => {
  hideClipboardToast();
});

// Check on window focus and every 2 seconds
window.addEventListener("focus", checkClipboardForSoundCloud);
setInterval(() => {
  if (document.hasFocus()) {
    checkClipboardForSoundCloud();
  }
}, 2500);

// ==============================================================================
// Floating Audio Mini-Player Controller
// ==============================================================================
function formatAudioTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

async function playTrackPreview(trackObj) {
  if (!trackObj || !trackObj.url) return;

  const sameTrack = currentPlayingUrl === trackObj.url;

  if (sameTrack) {
    if (previewAudio.paused) {
      previewAudio.play().catch(console.warn);
    } else {
      previewAudio.pause();
    }
    return;
  }

  // Switch to new track
  currentPlayingUrl = trackObj.url;
  currentPlayingIndex = trackObj.index !== undefined ? trackObj.index : null;

  playerTitle.textContent = trackObj.title || "SoundCloud Трек";
  playerArtist.textContent = trackObj.uploader || "SoundCloud Артист";
  const art = trackObj.artwork || currentMediaInfo?.artwork || "https://a-v2.sndcdn.com/assets/images/default/avatar-f000000000.png";
  playerThumb.src = art;

  playerCurrentTime.textContent = "0:00";
  playerTotalTime.textContent = trackObj.duration_formatted || (trackObj.duration ? formatAudioTime(trackObj.duration) : "--:--");
  playerSeekBar.value = 0;
  playerSeekProgress.style.width = "0%";

  audioMiniPlayer.style.display = "flex";
  updatePlayingUIState(false, true);

  try {
    const res = await fetch(`/api/stream_info?url=${encodeURIComponent(trackObj.url)}`);
    const data = await res.json();
    if (!res.ok || !data.stream_url) {
      throw new Error(data.error || "Не удалось получить аудиопоток трека");
    }

    if (currentPlayingUrl !== trackObj.url) return; // Discard if user clicked another track during fetch

    previewAudio.src = data.stream_url;
    previewAudio.currentTime = 0;
    await previewAudio.play();
  } catch (err) {
    console.error("Audio preview error:", err);
    updatePlayingUIState(false, false);
    showError(err.message || "Ошибка загрузки аудиопотока для предпрослушивания");
  }
}

function updatePlayingUIState(isPlaying, isLoading) {
  // Update mini-player controls
  if (isLoading) {
    playerLoadingSpinner.style.display = "block";
    playerPlayIcon.style.display = "none";
    playerPauseIcon.style.display = "none";
    playerWaveIndicator.style.display = "none";
  } else if (isPlaying) {
    playerLoadingSpinner.style.display = "none";
    playerPlayIcon.style.display = "none";
    playerPauseIcon.style.display = "block";
    playerWaveIndicator.style.display = "flex";
  } else {
    playerLoadingSpinner.style.display = "none";
    playerPlayIcon.style.display = "block";
    playerPauseIcon.style.display = "none";
    playerWaveIndicator.style.display = "none";
  }

  // Update single track artwork play button
  if (trackPlayBtn) {
    if (isPlaying && (!currentMediaInfo?.is_playlist || currentPlayingUrl === currentMediaInfo?.url)) {
      trackPlayBtn.classList.add("is-playing");
    } else {
      trackPlayBtn.classList.remove("is-playing");
    }
  }

  // Update playlist rows
  const rows = tracklistItems.querySelectorAll(".track-row");
  rows.forEach((row) => {
    const rowIdx = parseInt(row.dataset.index, 10);
    const isThisTrack = currentPlayingIndex !== null && rowIdx === currentPlayingIndex;
    if (isThisTrack && isPlaying) {
      row.classList.add("is-playing");
    } else {
      row.classList.remove("is-playing");
    }
  });
}

function stopAudioPreview() {
  previewAudio.pause();
  previewAudio.src = "";
  currentPlayingUrl = null;
  currentPlayingIndex = null;
  audioMiniPlayer.style.display = "none";
  updatePlayingUIState(false, false);
}

// Preview Audio Event Listeners
previewAudio.addEventListener("timeupdate", () => {
  if (isSeekingAudio) return;
  const cur = previewAudio.currentTime || 0;
  const dur = previewAudio.duration || 0;
  playerCurrentTime.textContent = formatAudioTime(cur);
  if (dur > 0) {
    const pct = (cur / dur) * 100;
    playerSeekBar.value = pct;
    playerSeekProgress.style.width = `${pct}%`;
  }
});

previewAudio.addEventListener("loadedmetadata", () => {
  playerTotalTime.textContent = formatAudioTime(previewAudio.duration || 0);
});

previewAudio.addEventListener("ended", () => {
  updatePlayingUIState(false, false);
  playerSeekBar.value = 0;
  playerSeekProgress.style.width = "0%";
  playerCurrentTime.textContent = "0:00";
});

previewAudio.addEventListener("play", () => updatePlayingUIState(true, false));
previewAudio.addEventListener("pause", () => updatePlayingUIState(false, false));
previewAudio.addEventListener("waiting", () => updatePlayingUIState(false, true));
previewAudio.addEventListener("playing", () => updatePlayingUIState(true, false));
previewAudio.addEventListener("error", (e) => {
  console.warn("Audio element playback error:", e);
  updatePlayingUIState(false, false);
});

// Mini-Player Control Listeners
playerPlayPauseBtn.addEventListener("click", () => {
  if (previewAudio.paused) {
    previewAudio.play().catch(console.warn);
  } else {
    previewAudio.pause();
  }
});

playerSeekBar.addEventListener("input", () => {
  isSeekingAudio = true;
  const dur = previewAudio.duration || 0;
  const pct = parseFloat(playerSeekBar.value);
  playerSeekProgress.style.width = `${pct}%`;
  if (dur > 0) {
    playerCurrentTime.textContent = formatAudioTime((pct / 100) * dur);
  }
});

playerSeekBar.addEventListener("change", () => {
  const dur = previewAudio.duration || 0;
  const pct = parseFloat(playerSeekBar.value);
  if (dur > 0) {
    previewAudio.currentTime = (pct / 100) * dur;
  }
  isSeekingAudio = false;
});

playerVolumeSlider.addEventListener("input", () => {
  const vol = parseFloat(playerVolumeSlider.value);
  previewAudio.volume = vol;
  if (vol === 0) {
    volumeIcon.style.display = "none";
    muteIcon.style.display = "block";
  } else {
    volumeIcon.style.display = "block";
    muteIcon.style.display = "none";
    lastVolume = vol;
  }
});

playerVolumeBtn.addEventListener("click", () => {
  if (previewAudio.volume > 0) {
    lastVolume = previewAudio.volume;
    previewAudio.volume = 0;
    playerVolumeSlider.value = 0;
    volumeIcon.style.display = "none";
    muteIcon.style.display = "block";
  } else {
    const restore = lastVolume > 0 ? lastVolume : 0.8;
    previewAudio.volume = restore;
    playerVolumeSlider.value = restore;
    volumeIcon.style.display = "block";
    muteIcon.style.display = "none";
  }
});

playerCloseBtn.addEventListener("click", stopAudioPreview);

// Initial Run
initSystem();
