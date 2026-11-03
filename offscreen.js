/**
 * offscreen.js - Handles DOM media capture and MediaRecorder execution
 * Runs inside the Chrome Extension Offscreen Document context.
 */

let mediaRecorder = null;
let recordedChunks = [];
let captureStream = null;
let micStream = null;
let audioContext = null;
let recordingMeta = {};
let recordingStartTime = 0;

// Keep latest recording in offscreen memory for immediate fallback access
window.latestRecording = null;

/**
 * Find the most suitable WebM codec supported by this browser
 */
function getBestSupportedMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm;codecs=h264,opus',
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm'
  ];

  for (const mime of candidates) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return '';
}

/**
 * Start tab media recording
 */
async function startCapture(message) {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    console.warn('Capture is already in progress.');
    return;
  }

  const { streamId, tabId, tabTitle, tabUrl, includeAudio, includeMic, resolution } = message;

  recordingMeta = {
    tabId,
    tabTitle: tabTitle || 'Active Tab',
    tabUrl: tabUrl || '',
    includeAudio: includeAudio !== false,
    includeMic: includeMic === true,
    resolution: resolution || '1080p'
  };

  // Video constraints
  const videoConstraints = {
    mandatory: {
      chromeMediaSource: 'tab',
      chromeMediaSourceId: streamId
    }
  };

  if (recordingMeta.resolution === '1080p') {
    videoConstraints.mandatory.maxWidth = 1920;
    videoConstraints.mandatory.maxHeight = 1080;
  } else if (recordingMeta.resolution === '720p') {
    videoConstraints.mandatory.maxWidth = 1280;
    videoConstraints.mandatory.maxHeight = 720;
  }

  // Audio constraints
  const audioConstraints = recordingMeta.includeAudio ? {
    mandatory: {
      chromeMediaSource: 'tab',
      chromeMediaSourceId: streamId
    }
  } : false;

  console.log('Requesting tab media stream with streamId:', streamId);

  // 1. Capture the tab stream
  captureStream = await navigator.mediaDevices.getUserMedia({
    audio: audioConstraints,
    video: videoConstraints
  });

  // 2. Tab Audio Routing:
  // When tabCapture captures audio, Chrome automatically mutes local tab playback.
  // We route the audio back to audioContext.destination so the user can still hear the tab audio!
  const hasTabAudio = captureStream.getAudioTracks().length > 0;
  try {
    audioContext = new AudioContext();
    if (hasTabAudio) {
      const tabSource = audioContext.createMediaStreamSource(captureStream);
      tabSource.connect(audioContext.destination);
    }
  } catch (audioErr) {
    console.warn('AudioContext routing error:', audioErr);
  }

  // 3. Optional Microphone mixing
  let finalStream = captureStream;
  if (recordingMeta.includeMic) {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!audioContext) audioContext = new AudioContext();
      const mixedDest = audioContext.createMediaStreamDestination();

      if (hasTabAudio) {
        const tabAudioSource = audioContext.createMediaStreamSource(captureStream);
        tabAudioSource.connect(mixedDest);
      }

      const micSource = audioContext.createMediaStreamSource(micStream);
      micSource.connect(mixedDest);

      finalStream = new MediaStream([
        ...captureStream.getVideoTracks(),
        ...mixedDest.stream.getAudioTracks()
      ]);
      console.log('Microphone successfully mixed with tab audio.');
    } catch (micErr) {
      console.warn('Microphone access could not be established; recording tab audio only:', micErr);
    }
  }

  // 4. Handle edge case: User closes the recorded tab
  const [videoTrack] = captureStream.getVideoTracks();
  if (videoTrack) {
    videoTrack.onended = () => {
      console.log('Tab video track ended (tab closed or stream aborted). Stopping recording.');
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopCapture();
      }
    };
  }

  // 5. Initialize MediaRecorder
  recordedChunks = [];
  const selectedMime = getBestSupportedMimeType();
  console.log('Starting MediaRecorder with mimeType:', selectedMime);

  mediaRecorder = new MediaRecorder(
    finalStream,
    selectedMime ? { mimeType: selectedMime } : undefined
  );

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
      console.log(`Received chunk #${recordedChunks.length}, size: ${event.data.size} bytes`);
    }
  };

  mediaRecorder.onstop = async () => {
    console.log('MediaRecorder stopped. Finalizing video blob...');
    const duration = Date.now() - recordingStartTime;
    const finalBlob = new Blob(recordedChunks, { type: selectedMime || 'video/webm' });
    console.log(`Final Blob size: ${finalBlob.size} bytes from ${recordedChunks.length} chunks.`);

    // Stop all media tracks
    if (captureStream) {
      captureStream.getTracks().forEach((track) => track.stop());
      captureStream = null;
    }
    if (micStream) {
      micStream.getTracks().forEach((track) => track.stop());
      micStream = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
      try {
        await audioContext.close();
      } catch (e) {
        console.warn('AudioContext close error:', e);
      }
      audioContext = null;
    }

    // Prepare recording record
    const recordingId = 'rec_' + Date.now();
    const record = {
      id: recordingId,
      blob: finalBlob,
      size: finalBlob.size,
      duration: duration,
      tabTitle: recordingMeta.tabTitle,
      tabUrl: recordingMeta.tabUrl,
      mimeType: finalBlob.type,
      createdAt: new Date().toISOString()
    };

    // Store in memory for immediate access
    window.latestRecording = record;

    try {
      // Save into IndexedDB and wait for disk commit
      await saveRecording(record);
      console.log('Recording safely committed to IndexedDB with ID:', recordingId);

      // Notify service worker that recording is ready
      chrome.runtime.sendMessage({
        action: 'RECORDING_SAVED',
        recordingId: recordingId,
        tabTitle: recordingMeta.tabTitle,
        duration: duration,
        size: finalBlob.size
      });
    } catch (saveErr) {
      console.error('Error saving recording to IndexedDB:', saveErr);
      // Still notify background so preview page can try to load from memory!
      chrome.runtime.sendMessage({
        action: 'RECORDING_SAVED',
        recordingId: recordingId,
        tabTitle: recordingMeta.tabTitle,
        duration: duration,
        size: finalBlob.size
      });
    }
  };

  recordingStartTime = Date.now();
  mediaRecorder.start(1000); // 1-second chunks
  console.log('Tab recording started successfully at', recordingStartTime);
}

/**
 * Stop tab media recording
 */
function stopCapture() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    try {
      // Request buffered data immediately so nothing is lost
      mediaRecorder.requestData();
    } catch (e) {
      console.warn('requestData error on stop:', e);
    }
    mediaRecorder.stop();
  } else {
    console.warn('Cannot stop capture; recorder is not recording.');
  }
}

// Listen for messages from background.js and preview.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'GET_OFFSCREEN_RECORDING') {
    if (window.latestRecording && (!message.recordingId || window.latestRecording.id === message.recordingId)) {
      sendResponse({
        success: true,
        record: window.latestRecording
      });
    } else {
      sendResponse({ success: false });
    }
    return false;
  }

  if (message.target !== 'offscreen') {
    return;
  }

  if (message.action === 'START_RECORDING_STREAM') {
    startCapture(message)
      .then(() => sendResponse({ success: true }))
      .catch((err) => {
        console.error('Failed to start capture:', err);
        sendResponse({ success: false, error: err.message });
      });
    return true; // Keep channel open for async response
  }

  if (message.action === 'STOP_RECORDING_STREAM') {
    stopCapture();
    sendResponse({ success: true });
    return false;
  }
});
