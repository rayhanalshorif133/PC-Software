/**
 * background.js - Service Worker for TabScreen Recorder
 * Controls the recording state machine, offscreen document lifecycle, and tab events.
 */

// Initialize or reset session storage on startup / install
chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.session.set({
    recordingState: 'idle',
    recordingTabId: null,
    recordingStartTime: null,
    recordingTabTitle: null,
    recordingTabUrl: null
  });
  await chrome.action.setBadgeText({ text: '' });
});

chrome.runtime.onStartup.addListener(async () => {
  await chrome.storage.session.set({
    recordingState: 'idle',
    recordingTabId: null,
    recordingStartTime: null,
    recordingTabTitle: null,
    recordingTabUrl: null
  });
  await chrome.action.setBadgeText({ text: '' });
});

/**
 * Ensure an offscreen document is open and ready to receive media streams
 */
async function ensureOffscreenDocument() {
  if (chrome.runtime.getContexts) {
    const contexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT']
    });
    if (contexts.length > 0) {
      return;
    }
  }

  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA', 'AUDIO_PLAYBACK', 'BLOBS'],
      justification: 'Recording specific browser tab audio and video'
    });
  } catch (err) {
    if (!err.message.includes('Only a single offscreen document may be created')) {
      throw err;
    }
  }
}

/**
 * Get media stream ID for the targeted active tab
 */
function getTabStreamId(tabId) {
  return new Promise((resolve, reject) => {
    chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, (streamId) => {
      if (chrome.runtime.lastError) {
        return reject(new Error(chrome.runtime.lastError.message));
      }
      if (!streamId) {
        return reject(new Error('Chrome failed to generate stream ID for this tab.'));
      }
      resolve(streamId);
    });
  });
}

/**
 * Start recording the specified tab
 */
async function handleStartRecording(tabId, options = {}) {
  const { recordingState } = await chrome.storage.session.get('recordingState');
  if (recordingState === 'recording' || recordingState === 'starting') {
    throw new Error('Recording is already in progress.');
  }

  await chrome.storage.session.set({ recordingState: 'starting' });

  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error('Tab not found.');
    }

    // Check if the URL is allowed by Chrome policies
    if (
      !tab.url ||
      tab.url.startsWith('chrome://') ||
      tab.url.startsWith('edge://') ||
      tab.url.startsWith('chrome-extension://') ||
      tab.url.startsWith('about:') ||
      tab.url.includes('chromewebstore.google.com') ||
      tab.url.includes('chrome.google.com/webstore')
    ) {
      throw new Error(
        'Chrome restrictions do not allow recording system pages (chrome://) or the Web Store. Please open any standard website (e.g., YouTube, Google, Wikipedia) and try again.'
      );
    }

    // 1. Obtain stream ID for the target tab
    const streamId = await getTabStreamId(tab.id);

    // 2. Ensure offscreen document is ready
    await ensureOffscreenDocument();

    // 3. Send START_RECORDING_STREAM message to the offscreen document
    await chrome.runtime.sendMessage({
      action: 'START_RECORDING_STREAM',
      target: 'offscreen',
      streamId: streamId,
      tabId: tab.id,
      tabTitle: tab.title || 'Tab',
      tabUrl: tab.url,
      includeAudio: options.includeAudio !== false,
      includeMic: options.includeMic === true,
      resolution: options.resolution || '1080p'
    });

    const now = Date.now();
    await chrome.storage.session.set({
      recordingState: 'recording',
      recordingTabId: tab.id,
      recordingStartTime: now,
      recordingTabTitle: tab.title || 'Tab',
      recordingTabUrl: tab.url
    });

    await chrome.action.setBadgeText({ text: 'REC' });
    await chrome.action.setBadgeBackgroundColor({ color: '#E53935' });

    return { success: true, startTime: now };
  } catch (err) {
    await chrome.storage.session.set({
      recordingState: 'idle',
      recordingTabId: null,
      recordingStartTime: null,
      recordingTabTitle: null,
      recordingTabUrl: null
    });
    await chrome.action.setBadgeText({ text: '' });
    throw err;
  }
}

/**
 * Stop active tab recording
 */
async function handleStopRecording() {
  const { recordingState } = await chrome.storage.session.get('recordingState');
  if (recordingState !== 'recording') {
    return { success: false, message: 'Not actively recording.' };
  }

  await chrome.storage.session.set({ recordingState: 'stopping' });

  chrome.runtime.sendMessage({
    action: 'STOP_RECORDING_STREAM',
    target: 'offscreen'
  });

  return { success: true };
}

// Global Message Listener (Popup, Offscreen, etc.)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'GET_STATUS') {
    (async () => {
      const state = await chrome.storage.session.get([
        'recordingState',
        'recordingTabId',
        'recordingStartTime',
        'recordingTabTitle',
        'recordingTabUrl'
      ]);
      sendResponse(state);
    })();
    return true; // Keep message channel open for async response
  }

  if (message.action === 'START_RECORDING') {
    (async () => {
      try {
        const result = await handleStartRecording(message.tabId, message.options);
        sendResponse({ success: true, data: result });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (message.action === 'STOP_RECORDING') {
    (async () => {
      try {
        const result = await handleStopRecording();
        sendResponse(result);
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (message.action === 'RECORDING_SAVED') {
    (async () => {
      console.log('Recording saved event received. Finalizing state for ID:', message.recordingId);
      await chrome.storage.session.set({
        recordingState: 'idle',
        recordingTabId: null,
        recordingStartTime: null,
        recordingTabTitle: null,
        recordingTabUrl: null
      });

      await chrome.action.setBadgeText({ text: '' });

      // DO NOT close offscreen document here!
      // Keeping the offscreen document alive prevents killing active IndexedDB write transactions
      // and allows the preview page to access any in-memory data if needed.

      // Open the preview tab so user can watch and download the recorded video
      const previewUrl = chrome.runtime.getURL(`preview.html?id=${message.recordingId}`);
      await chrome.tabs.create({ url: previewUrl });
    })();
    return false;
  }
});

// Automatically handle user closing the tab being recorded
chrome.tabs.onRemoved.addListener(async (closedTabId) => {
  const { recordingTabId, recordingState } = await chrome.storage.session.get([
    'recordingTabId',
    'recordingState'
  ]);

  if (recordingState === 'recording' && closedTabId === recordingTabId) {
    console.log('Recorded tab was closed by user. Stopping recording cleanly...');
    await handleStopRecording();
  }
});

// Keyboard shortcut command listener (Alt+Shift+R)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'toggle-recording') {
    const { recordingState } = await chrome.storage.session.get('recordingState');
    if (recordingState === 'recording') {
      await handleStopRecording();
    } else if (recordingState === 'idle' || !recordingState) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        await handleStartRecording(tab.id, {
          includeAudio: true,
          includeMic: false,
          resolution: '1080p'
        });
      }
    }
  }
});
