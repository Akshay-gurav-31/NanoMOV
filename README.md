<p align="center">
  <img src="logo.png" alt="NanoMOV Logo" width="80">
</p>

<h1 align="center">NanoMOV</h1>

<p align="center">
  <strong>In-browser MOV to MP4 converter</strong><br>
  100% client-side · No uploads · No file size limit · Lossless
</p>

<p align="center">
  <a href="https://nanomov.vercel.app">Live Demo</a> ·
  <a href="#features">Features</a> ·
  <a href="#how-it-works">How It Works</a> ·
  <a href="#getting-started">Getting Started</a>
</p>

<p align="center">
  <a href="https://nanomov.vercel.app"><img src="https://img.shields.io/badge/Live-nanomov.vercel.app-F59E0B?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Demo"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT"></a>
  <a href="."><img src="https://img.shields.io/badge/Server-None-brightgreen?style=for-the-badge" alt="No Server"></a>
  <a href="."><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge" alt="PRs Welcome"></a>
</p>

---

## About

NanoMOV is a free, open-source web tool that converts MOV (QuickTime) videos to MP4 in under a second, directly in your browser. No server, no uploads, no account.

Renaming `.mov` to `.mp4` does not work because the two use different container headers. NanoMOV rewrites the container metadata (ISOBMFF atoms) and keeps the video and audio streams untouched, so there is no re-encoding and no quality loss.

## Performance

| Method | 1 GB File | Quality | Privacy |
|---|---|---|---|
| Online converter (cloud re-encode) | 10-30 min | Lossy | Uploaded to server |
| FFmpeg local (`-c copy`) | 3-5 sec | Lossless | Local |
| **NanoMOV (browser)** | **< 1 sec** | **Lossless** | **Local** |

## Features

- **Instant conversion:** pure JavaScript remuxer, no re-encoding
- **Private:** files never leave your browser
- **No size limit:** multi-GB files handled via chunked streaming (`Blob.slice()`)
- **FastStart:** `moov` atom moved before `mdat` for instant web playback
- **Preview and rename:** check the output and rename it before download
- **Full-window drag and drop:** drop a file anywhere on the page
- **Smart caching:** last conversion stored in IndexedDB, auto-expires in 24 hours
- **Responsive and accessible:** works on all screen sizes, semantic HTML, ARIA support, keyboard navigation
- **Contact form:** built with Web3Forms, with client-side validation

## How It Works

NanoMOV parses the ISOBMFF structure using `DataView` and `Uint8Array`:

| Step | Description |
|---|---|
| Parse | Reads `ftyp`, `moov` and `mdat` box headers |
| Rewrite `ftyp` | Changes brand from `qt  ` to `isom`/`mp42` |
| Relocate `moov` | Moves it before `mdat` (FastStart) |
| Fix offsets | Recalculates `stco`/`co64` chunk offsets |
| Pass through `mdat` | Streams untouched via `Blob.slice()` |
| Fallback | Non-standard files use FFmpeg WASM (lazy-loaded) |

## Getting Started

**Online:** [nanomov.vercel.app](https://nanomov.vercel.app)

**Locally:**

```bash
git clone https://github.com/Akshay-gurav-31/NanoMOV.git
cd NanoMOV
python -m http.server 8080
# Open http://localhost:8080
```

You can also open `index.html` directly in a browser.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, vanilla CSS, JavaScript |
| Remuxer | Pure JS (`DataView` / `Uint8Array`) |
| Fallback | FFmpeg WASM (lazy-loaded) |
| Caching | IndexedDB |
| Contact form | Web3Forms |
| Hosting | Vercel |
| Runtime dependencies | None |

## Tests

Requires Python 3 and FFmpeg:

```bash
python tests/test_mov_converter.py
python tests/test_metadata_audit.py
python tests/test_isobmff_remux.py
python tests/test_streaming_remux.py
```

## Project Structure
