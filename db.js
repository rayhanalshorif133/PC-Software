/**
 * db.js - IndexedDB storage helper for TabScreen Recorder
 * Handles storing, fetching, and deleting recorded WebM video blobs safely.
 */

const DB_NAME = 'TabScreenRecorderDB';
const DB_VERSION = 1;
const STORE_NAME = 'recordings';

/**
 * Open or upgrade the IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('createdAt', 'createdAt', { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Failed to open IndexedDB'));
  });
}

/**
 * Save a recording record with its video Blob
 * Waits for transaction.oncomplete to guarantee data is completely flushed to disk.
 * @param {Object} recordingData 
 * @returns {Promise<string>} recording ID
 */
async function saveRecording(recordingData) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    store.put(recordingData);

    // CRITICAL: Must resolve on transaction.oncomplete, NOT request.onsuccess
    // This ensures large video blobs are 100% written to disk before proceeding.
    transaction.oncomplete = () => {
      console.log('IndexedDB transaction completed successfully for', recordingData.id);
      resolve(recordingData.id);
    };

    transaction.onerror = () => {
      console.error('IndexedDB transaction error:', transaction.error);
      reject(transaction.error || new Error('Transaction failed'));
    };

    transaction.onabort = () => {
      console.error('IndexedDB transaction aborted:', transaction.error);
      reject(new Error('Transaction aborted'));
    };
  });
}

/**
 * Get a specific recording by its ID (including the full Blob)
 * @param {string} id 
 * @returns {Promise<Object|null>}
 */
async function getRecording(id) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(id);

    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Get all recordings metadata (excluding heavy Blobs for performance)
 * @returns {Promise<Array<Object>>}
 */
async function getAllRecordingsMetadata() {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index('createdAt');
    const request = index.openCursor(null, 'prev'); // Most recent first
    const items = [];

    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        const val = cursor.value;
        items.push({
          id: val.id,
          tabTitle: val.tabTitle,
          tabUrl: val.tabUrl,
          duration: val.duration,
          size: val.size,
          mimeType: val.mimeType,
          createdAt: val.createdAt
        });
        cursor.continue();
      } else {
        resolve(items);
      }
    };

    request.onerror = () => reject(request.error);
  });
}

/**
 * Delete a recording by ID
 * @param {string} id 
 * @returns {Promise<void>}
 */
async function deleteRecording(id) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    store.delete(id);

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}

/**
 * Clear all recordings
 * @returns {Promise<void>}
 */
async function clearAllRecordings() {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    store.clear();

    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
}
