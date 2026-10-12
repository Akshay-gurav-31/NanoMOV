<p align="center">
  <img src="logo.png" alt="NanoMOV Logo" width="80">
</p>

<h1 align="center">NanoMOV</h1>

<p align="center">
  <strong>Ultra-Fast In-Browser MOV → MP4 Converter</strong><br>
  100% Client-Side · Zero Uploads · No File Size Limits · Instant Results
</p>

<p align="center">
  <a href="https://nanomov.vercel.app">🚀 Live Demo</a> &nbsp;·&nbsp;
  <a href="#features">Features</a> &nbsp;·&nbsp;
  <a href="#how-it-works">How It Works</a> &nbsp;·&nbsp;
  <a href="#getting-started">Get Started</a>
</p>

<p align="center">
  <a href="https://nanomov.vercel.app"><img src="https://img.shields.io/badge/Live-nanomov.vercel.app-F59E0B?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Demo"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript"><img src="https://img.shields.io/badge/Made%20with-JavaScript-f7df1e?style=for-the-badge&logo=javascript&logoColor=black" alt="Made with JS"></a>
  <a href="."><img src="https://img.shields.io/badge/Server-None-brightgreen?style=for-the-badge" alt="No Server"></a>
  <a href="."><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge" alt="PRs Welcome"></a>
</p>

---

## ⚡ What is NanoMOV?

**NanoMOV** is a free, open-source, fully offline web tool that converts MOV (QuickTime) videos to MP4 **in under a second** — directly in your browser. No servers, no uploads, no accounts. Everything runs 100% on your device.

> **Why not just rename `.mov` to `.mp4`?**  
> Because it doesn't work. MOV and MP4 use different container headers. NanoMOV rewrites the container metadata (ISOBMFF atoms) while keeping your video/audio bitstreams **bit-perfect** — zero quality loss, zero re-encoding.

---

## 🏆 Performance Comparison

| Method | 1 GB File | Quality Loss | Privacy |
|---|---|---|---|
| Online converter (cloud re-encode) | 10–30 minutes | ❌ Lossy | ❌ Uploaded to server |
| FFmpeg local (`-c copy`) | 3–5 seconds | ✅ None | ✅ Local |
| **NanoMOV (browser)** | **< 1 second** | **✅ None (bit-perfect)** | **✅ Never leaves device** |

---

## ✨ Features

### 🎬 MOV to MP4 Converter
- **Millisecond conversion** — pure JavaScript zero-copy stream remuxer
- **100% private** — your file never leaves your browser
- **No file size limit** — handles multi-GB recordings via chunk streaming (`Blob.slice()`)
- **Web FastStart** — `moov` atom relocated before `mdat` for instant web playback
- **In-browser preview** — play and verify your converted MP4 before downloading
- **Zero quality loss** — bit-perfect video and audio frames preserved
- **File renaming** — rename your output file before downloading

### 🖱️ Full-Window Drag & Drop
- Drag a `.mov` file **anywhere** on the page — a beautiful full-screen overlay appears
- Corner bracket animation inspired by professional video editing tools
- Works from desktop file explorer, Finder, or any file manager

### 💾 Smart Caching (IndexedDB)
- Converted videos are automatically cached in your browser using IndexedDB
- **24-hour auto-expiry** — cache cleans itself the next day
- Reload the page? Your last conversion is still there, ready to download

### 📱 Fully Responsive
- Optimized for desktop, tablet, and mobile
- Touch-friendly targets (44px minimum) for accessibility
- No horizontal scroll on any screen size

### ♿ Accessibility
- Proper semantic HTML5 structure
- Sequential heading hierarchy (`h1` → `h2` → `h3`)
- ARIA labels, roles, and live regions for screen readers
- Keyboard-navigable drop zone and controls

### 📬 Contact Form
- Built-in contact form powered by [Web3Forms](https://web3forms.com/)
- Client-side validation (name, email, message length)
- Live character counter (1000 char limit)
- No backend required

---

## 🔧 How It Works

### Stream Copy Remuxing (Pure JavaScript)

NanoMOV parses the **ISO Base Media File Format (ISOBMFF)** binary structure using `DataView` and `Uint8Array`:

```
┌──────────────────────────────────────────────┐
│  Input: .MOV (QuickTime Container)           │
│                                              │
│  ftyp [qt  ]  ──→  Rewritten: [isom/mp42]   │
│  moov        ──→  Moved BEFORE mdat          │
│   └─ stco/co64 → Chunk offsets recalculated  │
│  mdat        ──→  Untouched (zero-copy)      │
│                                              │
│  Output: .MP4 (ISO BMFF Container)           │
│  + FastStart (moov before mdat)              │
└──────────────────────────────────────────────┘
```

### Key Technical Details

| Step | What Happens |
|---|---|
| **Parse ISOBMFF** | Reads box headers (`ftyp`, `moov`, `mdat`) using binary `DataView` |
| **Rewrite `ftyp`** | Changes brand from `qt  ` to `isom`/`mp42` for universal compatibility |
| **Relocate `moov`** | Moves `moov` atom before `mdat` for web FastStart playback |
| **Fix `stco`/`co64`** | Recalculates all chunk offsets to match the new atom positions |
| **Zero-copy `mdat`** | Video/audio bitstreams passed through untouched via `Blob.slice()` |
| **Fallback** | Non-standard MOV files use FFmpeg WASM (lazy-loaded on demand) |

---

## 🚀 Getting Started

### Option 1: Use Online (Recommended)

Visit **[nanomov.vercel.app](https://nanomov.vercel.app)** — no install required.

### Option 2: Run Locally

```bash
git clone https://github.com/Akshay-gurav-31/NanoMOV.git
cd NanoMOV
```

**Open directly (no server needed):**
```bash
# Windows
start index.html

# macOS
open index.html

# Linux
xdg-open index.html
```

**Or serve with any HTTP server:**
```bash
python -m http.server 8080
# Open: http://localhost:8080
```

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Structure** | Semantic HTML5 |
| **Styling** | Vanilla CSS (critical CSS inlined) |
| **Typography** | [Inter](https://fonts.google.com/specimen/Inter) via Google Fonts |
| **Video Remuxer** | Pure JavaScript (`DataView` / `Uint8Array` binary parser) |
| **Fallback Engine** | FFmpeg WASM (lazy-loaded on demand) |
| **Caching** | IndexedDB (24-hour TTL auto-expiry) |
| **Contact Form** | [Web3Forms](https://web3forms.com/) API |
| **Hosting** | [Vercel](https://vercel.com/) |
| **Runtime Dependencies** | **Zero** (no npm, no bundler, no framework) |

---

## 🧪 Running Tests

Requires **Python 3** and **FFmpeg** installed:

```bash
python tests/test_mov_converter.py    # MOV to MP4 remuxer + faststart + codecs
python tests/test_metadata_audit.py   # EXIF and metadata pipeline
python tests/test_isobmff_remux.py    # ISOBMFF box parsing
python tests/test_streaming_remux.py  # Large file chunk streaming
```

---

## 📁 Project Structure

```
NanoMOV/
├── index.html        # Main app (critical CSS inlined)
├── style.css         # Full stylesheet
├── script.js         # Conversion engine + UI logic
├── logo.png          # Logo (PNG fallback)
├── logo.webp         # Logo (WebP, optimized)
├── sample.mov        # Test MOV file
├── sample_verified.mp4  # Expected conversion output
├── tests/            # Python test suite
│   ├── test_mov_converter.py
│   ├── test_metadata_audit.py
│   ├── test_isobmff_remux.py
│   └── test_streaming_remux.py
└── README.md
```

---

## 🌐 Browser Support

| Browser | Minimum Version |
|---|---|
| Chrome | 90+ |
| Edge | 90+ |
| Firefox | 88+ |
| Safari | 15+ |

---

## 🤝 Contributing

Pull requests are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feat/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feat/amazing-feature`)
5. **Open** a Pull Request

---

## 🔒 Privacy

NanoMOV processes everything **locally in your browser**:

- ✅ No file uploads to any server
- ✅ No analytics or tracking
- ✅ No cookies or sessions
- ✅ No accounts required
- ✅ Your files never leave your device
- ✅ Works fully offline after first load

---

## 👨‍💻 Built By

**Akshay Gurav** — AI/ML Engineer | Data Science

[![Portfolio](https://img.shields.io/badge/Portfolio-akshaygurav.vercel.app-2563EB?style=flat-square&logo=googlechrome&logoColor=white)](https://akshaygurav.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-Akshay--gurav--31-181717?style=flat-square&logo=github)](https://github.com/Akshay-gurav-31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-akshay--gurav-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/akshay---gurav/)
[![Instagram](https://img.shields.io/badge/Instagram-akshay._.gurav-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://www.instagram.com/akshay._.gurav/)
[![X](https://img.shields.io/badge/X-@AkshayGurav__-000000?style=flat-square&logo=x)](https://x.com/AkshayGurav_)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<p align="center">
  <sub>Made with ❤️ for the open-source community</sub><br>
  <a href="https://nanomov.vercel.app"><strong>Try NanoMOV →</strong></a>
</p>
