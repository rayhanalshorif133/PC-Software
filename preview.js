/**
 * preview.js - Video player, download controller, and recording manager
 */

let currentRecording = null;
let currentBlobUrl = null;

const videoPlayer = document.getElementById('videoPlayer');
const metaTitle = document.getElementById('metaTitle');
const metaUrl = document.getElementById('metaUrl');
const metaDuration = document.getElementById('metaDuration');
const metaSize = document.getElementById('metaSize');
const metaDate = document.getElementById('metaDate');

const downloadBtn = document.getElementById('downloadBtn');
const deleteBtn = document.getElementById('deleteBtn');
const viewAllBtn = document.getElementById('viewAllBtn');
const recordingCountBadge = document.getElementById('recordingCountBadge');
const clearAllBtn = document.getElementById('clearAllBtn');
const recordingsList = document.getElementById('recordingsList');
const emptyListNotice = document.getElementById('emptyListNotice');
const librarySection = document.getElementById('librarySection');
const playerSection = document.getElementById('playerSection');
const loadingIndicator = document.getElementById('loadingIndicator');
const notFoundNotice = document.getElementById('notFoundNotice');

/**
 * Format milliseconds into MM:SS or HH:MM:SS
 */
function formatDuration(ms) {
  if (!ms || isNaN(ms)) return '00:00';
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const pad = (n) => String(n).padStart(2, '0');

  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }
  return `${pad(minutes)}:${pad(seconds)}`;
}

/**
 * Format bytes into human-readable MB / KB
 */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Sanitize string for valid filenames
 */
function sanitizeFilename(text) {
  return (text || 'Tab_Recording')
    .replace(/[^a-zA-Z0-9_\-\u0980-\u09FF]/g, '_')
    .replace(/_+/g, '_')
    .slice(0, 50);
}

/**
 * Set and play a recording record
 */
function displayRecording(record) {
  currentRecording = record;

  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl);
  }

  currentBlobUrl = URL.createObjectURL(record.blob);
  videoPlayer.src = currentBlobUrl;
  videoPlayer.load();

  // Populate metadata
  metaTitle.textContent = record.tabTitle || 'ট্যাব রেকর্ডিং';
  metaUrl.textContent = record.tabUrl || 'Unknown URL';
  metaDuration.textContent = formatDuration(record.duration);
  metaSize.textContent = formatBytes(record.size || (record.blob ? record.blob.size : 0));
  metaDate.textContent = record.createdAt ? new Date(record.createdAt).toLocaleString('bn-BD') : '--';

  document.title = `${record.tabTitle || 'ট্যাব'} - রেকর্ডিং প্রিভিউ`;

  // Highlight in library list
  document.querySelectorAll('.recording-card').forEach((el) => {
    el.classList.toggle('active', el.dataset.id === record.id);
  });

  playerSection.classList.remove('hidden');
  loadingIndicator.classList.add('hidden');
  notFoundNotice.classList.add('hidden');
}

/**
 * Load and display a recording in the player with retries and fallback
 */
async function loadRecording(recordingId) {
  loadingIndicator.classList.remove('hidden');
  notFoundNotice.classList.add('hidden');

  try {
    let record = null;

    // Retry up to 4 times with increasing delay to allow IndexedDB commit
    for (let attempt = 1; attempt <= 4; attempt++) {
      record = await getRecording(recordingId);
      if (record && record.blob && record.blob.size > 0) {
        break;
      }
      if (attempt < 4) {
        await new Promise((resolve) => setTimeout(resolve, attempt * 250));
      }
    }

    // Fallback: Query offscreen document memory directly
    if (!record || !record.blob) {
      console.log('Querying offscreen document memory for fallback recording...');
      try {
        const offscreenRes = await chrome.runtime.sendMessage({
          action: 'GET_OFFSCREEN_RECORDING',
          recordingId: recordingId
        });
        if (offscreenRes && offscreenRes.success && offscreenRes.record) {
          record = offscreenRes.record;
        }
      } catch (err) {
        console.warn('Offscreen fallback error:', err);
      }
    }

    if (record && record.blob) {
      displayRecording(record);
      return;
    }

    // If still not found
    console.warn('Recording could not be found with ID:', recordingId);
    loadingIndicator.classList.add('hidden');
    notFoundNotice.classList.remove('hidden');
  } catch (err) {
    console.error('Failed to load recording:', err);
    loadingIndicator.classList.add('hidden');
    notFoundNotice.classList.remove('hidden');
  }
}

/**
 * Trigger file download for the current recording
 */
function downloadCurrentRecording() {
  if (!currentRecording || !currentBlobUrl) {
    alert('কোনো রেকর্ডিং লোড করা নেই।');
    return;
  }

  const dateStr = new Date(currentRecording.createdAt || Date.now())
    .toISOString()
    .replace(/[:T]/g, '-')
    .slice(0, 19);
  const cleanTitle = sanitizeFilename(currentRecording.tabTitle);
  const filename = `${cleanTitle}_${dateStr}.webm`;

  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = currentBlobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  setTimeout(() => {
    document.body.removeChild(a);
  }, 100);
}

/**
 * Refresh recordings library list
 */
async function refreshLibrary() {
  try {
    const list = await getAllRecordingsMetadata();
    recordingCountBadge.textContent = list.length;

    recordingsList.innerHTML = '';

    if (list.length === 0) {
      emptyListNotice.classList.remove('hidden');
      return;
    }

    emptyListNotice.classList.add('hidden');

    list.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'recording-card';
      card.dataset.id = item.id;
      if (currentRecording && currentRecording.id === item.id) {
        card.classList.add('active');
      }

      card.innerHTML = `
        <div class="rc-title" title="${item.tabTitle || ''}">${item.tabTitle || 'Unnamed Tab'}</div>
        <div class="rc-meta">
          <span>⏱ ${formatDuration(item.duration)}</span>
          <span>💾 ${formatBytes(item.size)}</span>
        </div>
        <div class="rc-meta">
          <span>📅 ${item.createdAt ? new Date(item.createdAt).toLocaleDateString() : ''}</span>
        </div>
        <div class="rc-actions">
          <button class="btn btn-sm btn-secondary rc-play-btn">▶ প্লে করুন</button>
        </div>
      `;

      card.addEventListener('click', () => {
        loadRecording(item.id);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });

      recordingsList.appendChild(card);
    });
  } catch (err) {
    console.error('Failed to refresh library:', err);
  }
}

// Event Listeners
downloadBtn.addEventListener('click', downloadCurrentRecording);

deleteBtn.addEventListener('click', async () => {
  if (!currentRecording) return;
  const confirmed = confirm(`আপনি কি নিশ্চিত যে "${currentRecording.tabTitle}" রেকর্ডিংটি মুছে ফেলতে চান?`);
  if (!confirmed) return;

  await deleteRecording(currentRecording.id);

  // Load next available or show empty
  const remaining = await getAllRecordingsMetadata();
  if (remaining.length > 0) {
    loadRecording(remaining[0].id);
  } else {
    currentRecording = null;
    if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
    videoPlayer.src = '';
    metaTitle.textContent = 'কোনো রেকর্ডিং নেই';
    metaUrl.textContent = '';
    metaDuration.textContent = '--:--';
    metaSize.textContent = '-- MB';
    metaDate.textContent = '--';
    playerSection.classList.add('hidden');
  }

  refreshLibrary();
});

clearAllBtn.addEventListener('click', async () => {
  const confirmed = confirm('আপনি কি নিশ্চিত যে সব রেকর্ডিং স্থায়ীভাবে মুছে ফেলতে চান?');
  if (!confirmed) return;

  await clearAllRecordings();
  currentRecording = null;
  if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
  videoPlayer.src = '';
  playerSection.classList.add('hidden');
  refreshLibrary();
});

viewAllBtn.addEventListener('click', () => {
  librarySection.scrollIntoView({ behavior: 'smooth' });
});

// Page Initialization
document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const targetId = params.get('id');

  await refreshLibrary();

  if (targetId) {
    await loadRecording(targetId);
  } else {
    // If no specific ID, load the most recent recording
    const all = await getAllRecordingsMetadata();
    if (all.length > 0) {
      await loadRecording(all[0].id);
    } else {
      loadingIndicator.classList.add('hidden');
      playerSection.classList.add('hidden');
    }
  }
});
