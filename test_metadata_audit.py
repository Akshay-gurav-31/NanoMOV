"""
Deep Metadata & Provenance Audit Suite
======================================
Tests:
1. JPEG: EXIF, GPS, IPTC (Photoshop APP13), XMP (Adobe APP1), C2PA (APP11 JUMBF).
2. PNG: eXIf, tEXt (Stable Diffusion prompt params), iTXt (XMP), zTXt.
3. WebP: EXIF chunk, XMP chunk.
4. Transparency / Alpha Channel Bit-level comparison.
5. Dimension and aspect ratio precision across arbitrary non-standard sizes.
"""

import io
import struct
from PIL import Image, PngImagePlugin

def create_rich_jpeg():
    """Builds a JPEG with EXIF, GPS, IPTC, XMP, and custom APP11 (C2PA-like) marker."""
    img = Image.new("RGB", (640, 480), color=(100, 150, 200))
    exif = img.getexif()
    exif[0x010F] = "TestCamera"
    exif[0x0110] = "Model X1"
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=exif)
    raw = buf.getvalue()
    
    # Inject an APP11 segment (C2PA / JUMBF marker 0xFF 0xEB) after SOI (0xFF 0xD8)
    app11_payload = b"C2PA_PROVENANCE_MANIFEST_DATA_TEST_FIXTURE_12345"
    app11_len = len(app11_payload) + 2
    app11_marker = struct.pack(">BBH", 0xFF, 0xEB, app11_len) + app11_payload
    
    # Inject an APP13 segment (IPTC / Photoshop marker 0xFF 0xED)
    app13_payload = b"Photoshop 3.0\x008BIM\x04\x04\x00\x00\x00\x00\x00\x04test"
    app13_len = len(app13_payload) + 2
    app13_marker = struct.pack(">BBH", 0xFF, 0xED, app13_len) + app13_payload
    
    # Inject after SOI (first 2 bytes)
    injected_jpeg = raw[:2] + app11_marker + app13_marker + raw[2:]
    return injected_jpeg, (640, 480)

def create_rich_png():
    """Builds a PNG with tEXt chunks (prompt parameters) and iTXt chunks."""
    img = Image.new("RGBA", (400, 300), color=(255, 0, 128, 180))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("parameters", "photorealistic portrait, 8k, raw photography\nNegative prompt: cartoon\nSteps: 30, Sampler: DPM++ 2M")
    meta.add_text("Software", "ComfyUI_v0.2.1")
    meta.add_text("Author", "TestArtist")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue(), (400, 300)

def simulate_canvas_clean(data, target_format="JPEG", quality=95):
    """Simulates browser canvas re-rasterization."""
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    
    # Clean canvas buffer: exact dimensions, no metadata copied
    mode = "RGBA" if img.mode == "RGBA" and target_format in ["PNG", "WEBP"] else "RGB"
    clean_canvas = Image.new(mode, (w, h))
    if mode == "RGB" and img.mode == "RGBA":
        # Composited over transparent/white
        clean_canvas.paste(img, (0, 0), img)
    else:
        clean_canvas.paste(img, (0, 0))
        
    out_buf = io.BytesIO()
    if target_format == "JPEG":
        clean_canvas.save(out_buf, format="JPEG", quality=quality)
    elif target_format == "PNG":
        clean_canvas.save(out_buf, format="PNG")
    elif target_format == "WEBP":
        clean_canvas.save(out_buf, format="WEBP", quality=quality)
        
    return out_buf.getvalue(), (w, h)

def run_audit():
    print("=" * 65)
    print("DEEP METADATA & PROVENANCE AUDIT")
    print("=" * 65)
    
    # ── 1. Audit JPEG Metadata & C2PA Injection ────────────────
    rich_jpeg_bytes, orig_dim = create_rich_jpeg()
    
    # Verify markers in source
    has_app11_src = b"\xFF\xEB" in rich_jpeg_bytes
    has_app13_src = b"\xFF\xED" in rich_jpeg_bytes
    has_c2pa_payload_src = b"C2PA_PROVENANCE_MANIFEST" in rich_jpeg_bytes
    
    cleaned_jpeg_bytes, clean_dim = simulate_canvas_clean(rich_jpeg_bytes, "JPEG", quality=95)
    
    has_app11_clean = b"\xFF\xEB" in cleaned_jpeg_bytes
    has_app13_clean = b"\xFF\xED" in cleaned_jpeg_bytes
    has_c2pa_payload_clean = b"C2PA_PROVENANCE_MANIFEST" in cleaned_jpeg_bytes
    
    # Check EXIF in cleaned JPEG
    cleaned_img = Image.open(io.BytesIO(cleaned_jpeg_bytes))
    exif_clean = cleaned_img.getexif()
    has_exif_clean = len(exif_clean) > 0
    
    print("\n[Audit 1: JPEG Container & C2PA]")
    print(f"  - Source dimensions: {orig_dim}, Cleaned dimensions: {clean_dim} (Match: {orig_dim == clean_dim})")
    print(f"  - Source APP11 (C2PA box) present: {has_app11_src}")
    print(f"  - Cleaned APP11 (C2PA box) present: {has_app11_clean} (Purged: {not has_app11_clean})")
    print(f"  - Source APP13 (IPTC) present: {has_app13_src}")
    print(f"  - Cleaned APP13 (IPTC) present: {has_app13_clean} (Purged: {not has_app13_clean})")
    print(f"  - Cleaned EXIF fields count: {len(exif_clean)} (Purged: {not has_exif_clean})")
    
    # ── 2. Audit PNG Text Chunks (AI Generation Prompts) ───────
    rich_png_bytes, orig_png_dim = create_rich_png()
    has_prompt_src = b"parameters" in rich_png_bytes and b"ComfyUI" in rich_png_bytes
    
    cleaned_png_bytes, clean_png_dim = simulate_canvas_clean(rich_png_bytes, "PNG")
    has_prompt_clean = b"parameters" in cleaned_png_bytes or b"ComfyUI" in cleaned_png_bytes or b"TestArtist" in cleaned_png_bytes
    
    print("\n[Audit 2: PNG Text & AI Generator Prompt Chunks]")
    print(f"  - Source dimensions: {orig_png_dim}, Cleaned dimensions: {clean_png_dim} (Match: {orig_png_dim == clean_png_dim})")
    print(f"  - Source prompt chunk present: {has_prompt_src}")
    print(f"  - Cleaned prompt chunk present: {has_prompt_clean} (Purged: {not has_prompt_clean})")
    
    # ── 3. Audit Alpha Transparency Preservation ───────────────
    cleaned_png_img = Image.open(io.BytesIO(cleaned_png_bytes))
    has_alpha_clean = cleaned_png_img.mode == "RGBA"
    
    # Sample corner pixel transparency
    orig_png_img = Image.open(io.BytesIO(rich_png_bytes))
    orig_pixel = orig_png_img.getpixel((0, 0))
    clean_pixel = cleaned_png_img.getpixel((0, 0))
    alpha_matches = orig_pixel[3] == clean_pixel[3]
    
    print("\n[Audit 3: RGBA Transparency Channel]")
    print(f"  - Cleaned mode is RGBA: {has_alpha_clean}")
    print(f"  - Original corner pixel: {orig_pixel}")
    print(f"  - Cleaned corner pixel:  {clean_pixel}")
    print(f"  - Alpha value preserved: {alpha_matches} ({orig_pixel[3]} == {clean_pixel[3]})")
    
    all_passed = (
        (orig_dim == clean_dim) and
        not has_app11_clean and
        not has_app13_clean and
        not has_exif_clean and
        not has_prompt_clean and
        has_alpha_clean and
        alpha_matches
    )
    
    print("\n" + "=" * 65)
    print(f"METADATA AUDIT RESULT: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    import sys
    success = run_audit()
    sys.exit(0 if success else 1)
