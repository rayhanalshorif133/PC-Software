/**
 * popup.js - Controller for TabScreen Recorder popup interface
 */

let activeTab = null;
let timerInterval = null;

// UI Elements
const restrictedAlert = document.getElementById('restrictedAlert');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');

const tabFavicon = document.getElementById('tabFavicon');
const tabTitle = document.getElementById('tabTitle');
const tabUrl = document.getElementById('tabUrl');

const idleStateView = document.getElementById('idleStateView');
const recordingStateView = document.getElementById('recordingStateView');

const tabAudioToggle = document.getElementById('tabAudioToggle');
const micAudioToggle = document.getElementById('micAudioToggle');
const resolutionSelect = document.getElementById('resolutionSelect');

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const recordTimer = document.getElementById('recordTimer');
const historyBtn = document.getElementById('historyBtn');

/**
 * Format milliseconds into HH:MM:SS or MM:SS string
 */
function formatDuration(ms) {
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
 * Start updating the live timer display
 */
function startTimer(startTime) {
  if (timerInterval) clearInterval(timerInterval);

  const update = () => {
    const elapsed = Date.now() - startTime;
    recordTimer.textContent = formatDuration(elapsed);
  };

  update();
  timerInterval = setInterval(update, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

/**
 * Check if the active tab's URL can be recorded
 */
function isTabCapturable(url) {
  if (!url) return false;
  return (
    !url.startsWith('chrome://') &&
    !url.startsWith('edge://') &&
    !url.startsWith('chrome-extension://') &&
    !url.startsWith('about:') &&
    !url.includes('chromewebstore.google.com') &&
    !url.includes('chrome.google.com/webstore')
  );
}

/**
 * Show error message
 */
function showError(msg) {
  errorMessage.textContent = msg;
  errorAlert.classList.remove('hidden');
}

function clearError() {
  errorAlert.classList.add('hidden');
}

/**
 * Initialize popup UI
 */
async function initPopup() {
  try {
    // 1. Get current active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    activeTab = tab;

    if (activeTab) {
      tabTitle.textContent = activeTab.title || 'Untitled Tab';
      tabUrl.textContent = activeTab.url || '';
      if (activeTab.favIconUrl) {
        tabFavicon.src = activeTab.favIconUrl;
      }

      // Check URL restriction
      if (!isTabCapturable(activeTab.url)) {
        restrictedAlert.classList.remove('hidden');
        startBtn.disabled = true;
      }
    }

    // 2. Query recording status from background service worker
    const status = await chrome.runtime.sendMessage({ action: 'GET_STATUS' });

    if (status && status.recordingState === 'recording') {
      // Actively recording!
      idleStateView.classList.add('hidden');
      recordingStateView.classList.remove('hidden');
      
      if (status.recordingTabTitle) {
        tabTitle.textContent = status.recordingTabTitle;
      }
      if (status.recordingTabUrl) {
        tabUrl.textContent = status.recordingTabUrl;
      }

      startTimer(status.recordingStartTime || Date.now());
    } else {
      // Idle state
      idleStateView.classList.remove('hidden');
      recordingStateView.classList.add('hidden');
      stopTimer();
    }
  } catch (err) {
    console.error('Initialization error:', err);
    showError(err.message);
  }
}

// Start Recording Button Handler
startBtn.addEventListener('click', async () => {
  clearError();

  if (!activeTab || !activeTab.id) {
    showError('কোনো সচল ট্যাব পাওয়া যায়নি।');
    return;
  }

  if (!isTabCapturable(activeTab.url)) {
    showError('Chrome সিস্টেম বা ব্রাউজার স্টোর পেজ রেকর্ড করা সম্ভব নয়। যেকোনো ওয়েবসাইট ওপেন করুন।');
    return;
  }

  const includeAudio = tabAudioToggle.checked;
  let includeMic = micAudioToggle.checked;
  const resolution = resolutionSelect.value;

  // If microphone is requested, request permissions in popup first so Chrome prompts the user if needed
  if (includeMic) {
    try {
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStream.getTracks().forEach((t) => t.stop()); // close prompt stream
    } catch (micErr) {
      console.warn('Microphone permission denied:', micErr);
      showError('মাইক্রোফোন পারমিশন পাওয়া যায়নি। মাইক্রোফোন ছাড়া রেকর্ড করা হচ্ছে...');
      includeMic = false;
      micAudioToggle.checked = false;
    }
  }

  startBtn.disabled = true;
  startBtn.textContent = 'শুরু হচ্ছে...';

  try {
    const response = await chrome.runtime.sendMessage({
      action: 'START_RECORDING',
      tabId: activeTab.id,
      options: {
        includeAudio,
        includeMic,
        resolution
      }
    });

    if (response && response.success) {
      idleStateView.classList.add('hidden');
      recordingStateView.classList.remove('hidden');
      startTimer(response.data.startTime || Date.now());
    } else {
      throw new Error(response?.error || 'রেকর্ডিং শুরু করা যায়নি।');
    }
  } catch (err) {
    console.error('Failed to start recording:', err);
    showError(err.message);
    startBtn.disabled = false;
    startBtn.innerHTML = '<span class="btn-icon-dot"></span><span>রেকর্ড শুরু করুন (Start Recording)</span>';
  }
});

// Stop Recording Button Handler
stopBtn.addEventListener('click', async () => {
  clearError();
  stopBtn.disabled = true;
  stopBtn.innerHTML = '<span>ভিডিও প্রসেস ও সেভ হচ্ছে...</span>';

  try {
    const response = await chrome.runtime.sendMessage({ action: 'STOP_RECORDING' });
    if (response && response.success) {
      stopTimer();
      // Service worker will open the preview page automatically. Close popup after brief moment.
      setTimeout(() => {
        window.close();
      }, 500);
    } else {
      throw new Error(response?.message || 'রেকর্ডিং বন্ধ করতে সমস্যা হয়েছে।');
    }
  } catch (err) {
    console.error('Failed to stop recording:', err);
    showError(err.message);
    stopBtn.disabled = false;
    stopBtn.innerHTML = '<span class="btn-icon-square"></span><span>রেকর্ড বন্ধ করুন (Stop & Save)</span>';
  }
});

// History / Past Recordings Link
historyBtn.addEventListener('click', () => {
  const historyUrl = chrome.runtime.getURL('preview.html?view=all');
  chrome.tabs.create({ url: historyUrl });
  window.close();
});

// Run initialization
document.addEventListener('DOMContentLoaded', initPopup);

