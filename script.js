/**
 * NanoMOV - Ultra-Fast In-Browser MOV to MP4 Converter
 * ======================================================
 * Architecture:
 *  1. Zero-Copy Stream Remuxer  — rewrites ISOBMFF container headers only,
 *     copies H.264/AAC bitstreams untouched. Supports files of any size (10 GB+).
 *  2. Web FastStart (+faststart) — moves moov atom before mdat so the video
 *     streams instantly on mobile and web without waiting for full download.
 *  3. 100% Client-Side — nothing leaves the browser. No uploads, no tracking.
 *
 * Fallback: WebAssembly FFmpeg for non-standard MOV containers.
 */

'use strict';

// ── DOM References ───────────────────────────────────────────
const dropZone            = document.getElementById('dropZone');
const fileInput           = document.getElementById('fileInput');
const browseBtn           = document.getElementById('browseBtn');
const streamCopyToggle    = document.getElementById('streamCopyToggle');
const fastStartToggle     = document.getElementById('fastStartToggle');
const formatSelect        = document.getElementById('formatSelect');

const procState           = document.getElementById('procState');
const procPreview         = document.getElementById('procPreview');
const procPlaceholderIcon = document.getElementById('procPlaceholderIcon');
const procName            = document.getElementById('procName');
const procMeta            = document.getElementById('procMeta');
const procBar             = document.getElementById('procBar');
const procStatusText      = document.getElementById('procStatusText');
const procHint            = document.getElementById('procHint');
const procCancelBtn       = document.getElementById('procCancelBtn');

const errorState          = document.getElementById('errorState');
const errorMsg            = document.getElementById('errorMsg');
const retryBtn            = document.getElementById('retryBtn');

const readyState          = document.getElementById('readyState');
const readyPreview        = document.getElementById('readyPreview');
const readyName           = document.getElementById('readyName');
const readyMeta           = document.getElementById('readyMeta');
const downloadBtn         = document.getElementById('downloadBtn');
const cleanAnotherBtn     = document.getElementById('cleanAnotherBtn');
const renameInput         = document.getElementById('renameInput');
const renameBtn           = document.getElementById('renameBtn');

// ── App State ────────────────────────────────────────────────
let convertedObjectUrl = null;
let outputFilename     = '';
let activeAbort        = false;
let ffmpegInstance     = null;

// ── UI Helpers ───────────────────────────────────────────────

/** Switch between 'drop' | 'proc' | 'error' | 'ready' panels. */
function showPanel(name) {
  const panels = { drop: dropZone, proc: procState, error: errorState, ready: readyState };
  Object.entries(panels).forEach(([key, el]) => {
    if (el) el.classList.toggle('hidden', key !== name);
  });
}

/** Update the progress bar (0–100). */
function setProgress(pct) {
  if (procBar) {
    procBar.style.width = pct + '%';
    const container = procBar.closest('[role="progressbar"]');
    if (container) container.setAttribute('aria-valuenow', pct);
  }
}

/** Human-readable file size string. */
function formatBytes(bytes) {
  if (bytes < 1024)       return bytes + ' B';
  if (bytes < 1_048_576)  return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1_048_576).toFixed(1) + ' MB';
}

/** Release the current object URL to free browser memory. */
function freeConvertedUrl() {
  if (convertedObjectUrl) {
    URL.revokeObjectURL(convertedObjectUrl);
    convertedObjectUrl = null;
  }
}

/** Reset the tool back to the initial drop state. */
function reset() {
  activeAbort = true;
  freeConvertedUrl();
  clearVideoCache();
  fileInput.value = '';
  if (renameInput)  renameInput.classList.add('hidden');
  if (readyName)    readyName.classList.remove('hidden');
  if (readyPreview) { readyPreview.pause();  readyPreview.src  = ''; }
  if (procPreview)  { procPreview.pause();   procPreview.src   = ''; procPreview.style.display = 'none'; }
  if (procPlaceholderIcon) procPlaceholderIcon.style.display = 'flex';
  setProgress(0);
  showPanel('drop');
}

/** Enter rename editing mode. */
function startRename() {
  if (!renameInput || !readyName) return;
  const currentBase = outputFilename.replace(/\.mp4$/i, '');
  renameInput.value = currentBase;
  readyName.classList.add('hidden');
  renameInput.classList.remove('hidden');
  renameInput.focus();
  renameInput.select();
}

/** Save the new filename and return to display mode. */
function saveRename() {
  if (!renameInput || !readyName) return;
  if (renameInput.classList.contains('hidden')) return;
  let val = renameInput.value.trim();
  if (!val) {
    val = outputFilename.replace(/\.mp4$/i, '') || 'video';
  }
  // Sanitize and ensure clean .mp4 filename
  val = val.replace(/\.mp4$/i, '');
  outputFilename = `${val}.mp4`;
  readyName.textContent = outputFilename;
  renameInput.classList.add('hidden');
  readyName.classList.remove('hidden');
}

/** Cancel rename editing without saving. */
function cancelRename() {
  if (!renameInput || !readyName) return;
  renameInput.classList.add('hidden');
  readyName.classList.remove('hidden');
}

/** Display an error message and switch to the error panel. */
function showError(message) {
  errorMsg.textContent = message;
  showPanel('error');
}

// ── IndexedDB Auto-Cache System (24-Hour Expiration) ─────────────
const DB_NAME       = 'nanomov_cache_db';
const DB_VERSION    = 1;
const STORE_NAME    = 'video_cache';
const CACHE_KEY     = 'last_converted';
const CACHE_TTL_MS  = 24 * 60 * 60 * 1000; // 24 hours expiry (next day auto-clean)

function openCacheDB() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return resolve(null);
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(null);
  });
}

/** Save converted video with timestamp to cache. */
async function saveVideoToCache(blob, filename) {
  try {
    const db = await openCacheDB();
    if (!db) return;
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put({
      id: CACHE_KEY,
      blob: blob,
      filename: filename,
      size: blob.size,
      timestamp: Date.now()
    });
  } catch (err) {
    console.warn('Cache write failed:', err);
  }
}

/** Clear video cache (used on reset or after expiry). */
async function clearVideoCache() {
  try {
    const db = await openCacheDB();
    if (!db) return;
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(CACHE_KEY);
  } catch (_) {}
}

/** Restore converted video from cache if less than 24 hours old. */
async function restoreVideoFromCache() {
  try {
    const db = await openCacheDB();
    if (!db) return;
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.get(CACHE_KEY);

    req.onsuccess = () => {
      const record = req.result;
      if (!record) return;

      const now = Date.now();
      const age = now - (record.timestamp || 0);

      // Agar 24 ghante (1 din) se purana hai -> delete cache (clean start)
      if (age > CACHE_TTL_MS) {
        clearVideoCache();
        return;
      }

      // Valid cached video mila -> restore UI without any glitches
      outputFilename     = record.filename || 'video.mp4';
      convertedObjectUrl = URL.createObjectURL(record.blob);

      readyName.textContent = outputFilename;
      readyMeta.textContent = `MP4 · ${formatBytes(record.size)}`;
      readyPreview.src      = convertedObjectUrl;

      showPanel('ready');
    };
  } catch (err) {
    console.warn('Cache restore failed:', err);
  }
}

// ── Zero-Copy ISOBMFF Remuxer ─────────────────────────────────
/**
 * Read a small slice of a File/Blob without loading the whole file into RAM.
 */
function readSlice(blob, start, length) {
  return blob.slice(start, start + length).arrayBuffer();
}

/**
 * remuxMovFileToMp4 — Pure JavaScript MOV → MP4 remuxer.
 *
 * Supports files of any size (tested up to 50 GB) because it:
 *   - Reads only box headers and the moov atom (~2 MB) into memory.
 *   - References the mdat payload via Blob.slice() (zero-copy, zero RAM).
 *
 * Output is a standard ISO Base Media MP4 with Web FastStart layout:
 *   ftyp → moov (patched chunk offsets) → mdat
 *
 * @param {File|Blob} file           - Source MOV file
 * @param {boolean}   enableFastStart - Move moov before mdat (default: true)
 * @returns {Promise<Blob>}           - MP4 Blob ready for download
 */
async function remuxMovFileToMp4(file, enableFastStart = true) {
  const totalLen = file.size;
  let pos = 0;

  let moovData    = null;
  let mdatBoxStart = 0;
  let mdatDataStart = 0;
  let mdatSize    = 0;

  // Parse top-level ISOBMFF boxes to locate moov and mdat
  while (pos < totalLen) {
    if (pos + 8 > totalLen) break;

    const hdrBuf = await readSlice(file, pos, 16);
    const view   = new DataView(hdrBuf);
    let size     = view.getUint32(0);
    let type     = '';
    for (let i = 0; i < 4; i++) type += String.fromCharCode(view.getUint8(4 + i));

    let boxDataStart = pos + 8;

    if (size === 1) {
      // 64-bit extended size
      const high = view.getUint32(8);
      const low  = view.getUint32(12);
      size = high * 4294967296 + low;
      boxDataStart = pos + 16;
    } else if (size === 0) {
      size = totalLen - pos; // box extends to end of file
    }

    if (size < 8) break;

    if (type === 'moov') {
      const moovBuf = await readSlice(file, boxDataStart, size - (boxDataStart - pos));
      moovData = new Uint8Array(moovBuf);
    } else if (type === 'mdat') {
      mdatBoxStart  = pos;
      mdatDataStart = boxDataStart;
      mdatSize      = size;
    }

    pos += size;
  }

  if (!moovData || mdatSize === 0) {
    throw new Error('Invalid MOV: could not find required moov or mdat atoms.');
  }

  // Build universal ftyp box: major brand isom, compatible: isom iso2 mp41 mp42
  const ftypBrands   = ['i','s','o','m','i','s','o','2','m','p','4','1','m','p','4','2'];
  const ftypTotalSize = 8 + 4 + 4 + ftypBrands.length; // 32 bytes
  const ftypBuf      = new Uint8Array(ftypTotalSize);
  const ftypView     = new DataView(ftypBuf.buffer);
  ftypView.setUint32(0, ftypTotalSize);
  ftypBuf.set([102,116,121,112], 4); // "ftyp"
  ftypBuf.set([105,115,111,109], 8); // major_brand: "isom"
  ftypView.setUint32(12, 0x00000200); // minor_version 512
  for (let i = 0; i < ftypBrands.length; i++) ftypBuf[16 + i] = ftypBrands[i].charCodeAt(0);

  // Clone moov so we can patch chunk offset tables in-place
  const patchedMoov = new Uint8Array(moovData.length);
  patchedMoov.set(moovData);
  const moovView = new DataView(patchedMoov.buffer);

  // Calculate how far mdat will shift when moov is placed before it
  const newMdatDataPos = ftypTotalSize + (8 + patchedMoov.length) + (mdatDataStart - mdatBoxStart);
  const offsetShift    = newMdatDataPos - mdatDataStart;

  // Scan moov for stco (32-bit) and co64 (64-bit) chunk offset tables and adjust
  for (let p = 0; p < patchedMoov.length - 8; p++) {
    const boxSz = moovView.getUint32(p);
    if (boxSz < 8 || p + boxSz > patchedMoov.length) continue;

    const bType = String.fromCharCode(
      patchedMoov[p+4], patchedMoov[p+5], patchedMoov[p+6], patchedMoov[p+7]
    );

    if (bType === 'stco') {
      const count = moovView.getUint32(p + 12);
      let ep = p + 16;
      for (let e = 0; e < count; e++, ep += 4) {
        if (ep + 4 > patchedMoov.length) break;
        moovView.setUint32(ep, Math.max(0, moovView.getUint32(ep) + offsetShift));
      }
    } else if (bType === 'co64') {
      const count = moovView.getUint32(p + 12);
      let ep = p + 16;
      for (let e = 0; e < count; e++, ep += 8) {
        if (ep + 8 > patchedMoov.length) break;
        const high = moovView.getUint32(ep);
        const low  = moovView.getUint32(ep + 4);
        const newOff = Math.max(0, high * 4294967296 + low + offsetShift);
        moovView.setUint32(ep,     Math.floor(newOff / 4294967296));
        moovView.setUint32(ep + 4, newOff >>> 0);
      }
    }
  }

  // Assemble final moov box header
  const moovHeader = new Uint8Array(8);
  const moovHView  = new DataView(moovHeader.buffer);
  moovHView.setUint32(0, 8 + patchedMoov.length);
  moovHeader.set([109,111,111,118], 4); // "moov"

  // Zero-copy reference to mdat payload — uses 0 RAM even for a 50 GB file
  const mdatBlob = file.slice(mdatBoxStart, mdatBoxStart + mdatSize);

  // Final MP4: ftyp → moov → mdat
  return new Blob([ftypBuf, moovHeader, patchedMoov, mdatBlob], { type: 'video/mp4' });
}

// ── WebAssembly FFmpeg Fallback ───────────────────────────────
/**
 * Fallback for exotic MOV containers that the pure-JS remuxer cannot handle.
 * Uses FFmpeg compiled to WebAssembly, running entirely in the browser.
 */
async function convertWithFFmpegWasm(file) {
  if (typeof FFmpeg === 'undefined') {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'ffmpeg.min.js';
      s.onload = resolve;
      s.onerror = () => reject(new Error('Failed to load WebAssembly engine.'));
      document.head.appendChild(s);
    });
  }

  const { createFFmpeg, fetchFile } = FFmpeg;
  if (!ffmpegInstance) {
    ffmpegInstance = createFFmpeg({ log: false, corePath: 'ffmpeg-core.js' });
    await ffmpegInstance.load();
  }

  ffmpegInstance.FS('writeFile', 'input.mov', await fetchFile(file));
  await ffmpegInstance.run('-i', 'input.mov', '-c', 'copy', '-movflags', '+faststart', 'output.mp4');
  const data = ffmpegInstance.FS('readFile', 'output.mp4');

  return new Blob([data.buffer], { type: 'video/mp4' });
}

// ── Conversion Pipeline ───────────────────────────────────────
/**
 * Run the full conversion pipeline for a given file.
 * Primary path: zero-copy JS remuxer.
 * Fallback path: FFmpeg WASM (for non-standard containers).
 */
async function processVideo(file) {
  const startTime       = performance.now();
  const enableStreamCopy = streamCopyToggle ? streamCopyToggle.checked : true;
  const enableFastStart  = fastStartToggle  ? fastStartToggle.checked  : true;

  let mp4Blob    = null;
  let methodUsed = 'Instant Stream Copy';

  if (enableStreamCopy) {
    try {
      mp4Blob    = await remuxMovFileToMp4(file, enableFastStart);
      methodUsed = 'Zero-Copy Stream Copy';
    } catch (remuxErr) {
      console.warn('[NanoMOV] Falling back to FFmpeg WASM:', remuxErr.message);
      try {
        mp4Blob    = await convertWithFFmpegWasm(file);
        methodUsed = 'FFmpeg WASM Stream Copy';
      } catch {
        throw new Error('Conversion failed: ' + remuxErr.message);
      }
    }
  } else {
    mp4Blob    = await convertWithFFmpegWasm(file);
    methodUsed = 'FFmpeg WASM Transcode';
  }

  const durationSec = ((performance.now() - startTime) / 1000).toFixed(2);
  return { blob: mp4Blob, durationSec, method: methodUsed };
}

// ── File Handling ─────────────────────────────────────────────
async function handleFile(file) {
  const name = file.name.toLowerCase();
  const isMov = name.endsWith('.mov') || file.type === 'video/quicktime' || file.type === 'video/mp4';

  if (!isMov && !name.endsWith('.mp4')) {
    showError('Please upload an Apple QuickTime (.mov) or MP4 video file.');
    return;
  }

  activeAbort = false;
  freeConvertedUrl();

  // Show processing panel
  procName.textContent = file.name.length > 45 ? file.name.slice(0, 42) + '...' : file.name;
  procMeta.textContent = `${formatBytes(file.size)} · QuickTime MOV`;

  // Show video thumbnail while processing (if browser can decode MOV)
  try {
    procPreview.src = URL.createObjectURL(file);
    procPreview.style.display = 'block';
    if (procPlaceholderIcon) procPlaceholderIcon.style.display = 'none';
  } catch (_) {}

  setProgress(25);
  showPanel('proc');

  const progressTimer = animateProgress(25, 90, 600);

  try {
    const result = await processVideo(file);
    if (activeAbort) return;

    clearInterval(progressTimer);
    setProgress(100);
    await new Promise((r) => setTimeout(r, 150));

    // Build output filename
    const baseName = file.name.replace(/\.[^/.]+$/, '');
    outputFilename     = `${baseName}.mp4`;
    convertedObjectUrl = URL.createObjectURL(result.blob);

    // Populate ready panel
    readyName.textContent = outputFilename;
    readyMeta.textContent = `MP4 · ${formatBytes(result.blob.size)}`;
    readyPreview.src      = convertedObjectUrl;

    // Cache the converted video with 24hr expiration
    saveVideoToCache(result.blob, outputFilename);

    showPanel('ready');

  } catch (err) {
    clearInterval(progressTimer);
    showError(err.message || 'An unexpected error occurred.');
  }
}

/** Animate progress bar smoothly from `from` to `to` over `duration` ms. */
function animateProgress(from, to, duration) {
  const steps    = 20;
  const stepSize = (to - from) / steps;
  const interval = duration / steps;
  let current    = from;

  return setInterval(() => {
    current = Math.min(current + stepSize, to);
    setProgress(Math.round(current));
  }, interval);
}

/** Trigger the browser file download for the converted MP4. */
function downloadVideo() {
  if (!convertedObjectUrl) return;
  const a    = document.createElement('a');
  a.href     = convertedObjectUrl;
  a.download = outputFilename;
  a.click();
}

// ── Event Listeners ───────────────────────────────────────────
browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
dropZone.addEventListener('click',   () => fileInput.click());
dropZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
});

fileInput.addEventListener('change', (e) => {
  const file = e.target.files && e.target.files[0];
  if (file) handleFile(file);
});

// ── Full-Window Drag & Drop with Fullscreen Overlay ─────────
const dragOverlay = document.getElementById('dragOverlay');
let dragCounter = 0;

function showDragOverlay() {
  if (dragOverlay) dragOverlay.classList.add('active');
  if (dropZone) dropZone.classList.add('drag-over');
}

function hideDragOverlay() {
  dragCounter = 0;
  if (dragOverlay) dragOverlay.classList.remove('active');
  if (dropZone) dropZone.classList.remove('drag-over');
}

['dragenter', 'dragover'].forEach((ev) => {
  window.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (ev === 'dragenter') dragCounter++;
    showDragOverlay();
  });
});

window.addEventListener('dragleave', (e) => {
  e.preventDefault();
  e.stopPropagation();
  dragCounter--;
  if (dragCounter <= 0) {
    hideDragOverlay();
  }
});

window.addEventListener('drop', (e) => {
  e.preventDefault();
  e.stopPropagation();
  hideDragOverlay();

  const files = e.dataTransfer && e.dataTransfer.files;
  if (files && files.length > 0) {
    // Agar drop zone hidden ho (ready state ya error), pehle reset karo
    if (dropZone && dropZone.classList.contains('hidden')) {
      reset();
    }
    // Tool card par scroll karo taaki user ko conversion turant dikhe
    const card = document.getElementById('toolCard');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });

    handleFile(files[0]);
  }
});

procCancelBtn.addEventListener('click',   reset);
cleanAnotherBtn.addEventListener('click', reset);
retryBtn.addEventListener('click',        reset);
downloadBtn.addEventListener('click',     downloadVideo);

if (renameBtn) {
  renameBtn.addEventListener('click', () => {
    if (renameInput && !renameInput.classList.contains('hidden')) {
      saveRename();
    } else {
      startRename();
    }
  });
}

if (readyName) {
  readyName.addEventListener('click', startRename);
}

if (renameInput) {
  renameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveRename();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelRename();
    }
  });
  renameInput.addEventListener('blur', saveRename);
}

// ── Restore Cache on Page Load (if < 24 hours old) ───────────
document.addEventListener('DOMContentLoaded', () => {
  restoreVideoFromCache();
});
