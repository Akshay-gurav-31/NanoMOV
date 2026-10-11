# NanoMOV ⚡

> **Ultra-Fast In-Browser MOV → MP4 Converter + AI Image Anonymizer**  
> 100% Client-Side · Zero Uploads · No File Size Limits · Instant Results

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Made with JS](https://img.shields.io/badge/Made%20with-JavaScript-f7df1e?logo=javascript)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![No Server](https://img.shields.io/badge/Server-None-brightgreen)](.)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](.)

---

## What is NanoMOV?

NanoMOV is a **free, open-source, fully offline web tool** that runs entirely in your browser. It ships two powerful utilities:

| Tool | What it does |
|---|---|
| 🎬 **NanoMOV Converter** | Converts `.mov` (QuickTime) to `.mp4` in milliseconds via zero-copy stream remuxing — no re-encoding, no quality loss |
| 🎞️ **Analog Camera Studio** | Strips AI-generation fingerprints from images and re-applies authentic 35mm film grain + real camera EXIF metadata |

No servers. No uploads. No accounts. Everything happens on your device.

---

## Why is NanoMOV Insanely Fast?

Traditional converters upload your video to a server, re-encode every frame (lossy, slow), and put you in a queue.

**NanoMOV uses Stream Copy Remuxing:**

- `.mov` and `.mp4` share the **same underlying H.264/AAC bitstream**
- NanoMOV simply **rewrites the container header** — no decoding, no encoding
- Adds **Web FastStart** (`+faststart`) by moving `moov` atom before `mdat`
- Recalculates all chunk offsets (`stco` / `co64`) for byte-perfect output
- **Multi-gigabyte support** via `Blob.slice()` zero-copy streaming (never loads full file into RAM)

### Performance Comparison

| Method | 1 GB file | Quality Loss |
|---|---|---|
| Online converter (cloud re-encode) | ~10–30 minutes | Lossy |
| FFmpeg local (`-c copy`) | ~3–5 seconds | None |
| **NanoMOV (browser)** | **< 1 second** | **0.00% (bit-perfect)** |

---

## Features

### 🎬 MOV → MP4 Converter
- ⚡ **Millisecond conversion** — pure JS zero-copy stream remuxer
- 🔒 **100% private** — your file never leaves your browser
- 📦 **No file size limit** — handles multi-GB recordings via chunk streaming
- 🎯 **Web FastStart** — `moov` relocated to front for instant web playback
- 🎥 **In-browser preview** — play your converted MP4 before downloading
- 💯 **Zero quality loss** — bit-perfect video and audio frames

### 🎞️ Analog Camera Studio
- 🧹 Strips AI-generation metadata fingerprints from images
- 🌿 Applies authentic **35mm film grain** to break diffusion lattice patterns
- 🔮 Adds real **optical vignetting** (simulates camera lens falloff)
- 📷 Injects authentic **Apple iPhone 15 Pro EXIF metadata**
- 🔁 Runs **96% resize cycles** to disrupt AI upscaling artifacts
- Works entirely offline — no API keys required

---

## Usage

### Open Directly (No Install)
```bash
git clone https://github.com/YOUR_USERNAME/NanoMOV.git
cd NanoMOV

# Windows
start index.html

# macOS
open index.html

# Linux
xdg-open index.html
```

### Serve Locally
```bash
python -m http.server 8080
# Then open: http://localhost:8080
```

---

## How It Works (Technical)

### MOV → MP4 Remuxer (Pure JavaScript)

The remuxer parses ISO Base Media File Format (ISOBMFF) binary structure:

```
ftyp  → Rewritten: qt → isom/mp42
moov  → Moved BEFORE mdat (+faststart)
  └─ stco/co64 → Chunk offsets recalculated
mdat  → Untouched (zero-copy passthrough)
```

### Analog Camera Studio Pipeline

```
Input → [Strip Metadata] → [96% Resize Cycle] → [Film Grain]
      → [Optical Vignette] → [EXIF Injection] → Output
```

---

## Running Tests

Requires Python 3 and FFmpeg:

```bash
python tests/test_mov_converter.py    # MOV→MP4 remuxer + faststart + codecs
python tests/test_metadata_audit.py   # EXIF/metadata pipeline
python tests/test_isobmff_remux.py    # ISOBMFF box parsing
python tests/test_streaming_remux.py  # Large file chunk streaming
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Structure | Semantic HTML5 |
| Styling | Vanilla CSS |
| Video Remuxer | Pure JavaScript (DataView / Uint8Array) |
| Image Processing | HTML5 Canvas API |
| EXIF Writing | Custom binary EXIF encoder |
| Dependencies | **Zero** |

---

## Browser Support

Chrome 90+, Edge 90+, Firefox 88+, Safari 15+

---

## License

MIT — free to use, modify, and distribute.

---

## Privacy

- ❌ No file uploads · ❌ No analytics · ❌ No cookies  
- ✅ Your files never leave your device
