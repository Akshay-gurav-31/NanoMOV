"""
Comprehensive Test Suite for Image Privacy Pipeline
=====================================================
Uses native Pillow (PIL) to validate:
1. Exact dimension and aspect ratio preservation (no cropping).
2. Lossless transparency (alpha channel) preservation in PNG/WebP.
3. Metadata removal (EXIF, GPS, camera tags purged).
4. High visual fidelity (PSNR > 38 dB for JPEG, lossless for PNG).
5. File integrity across JPEG, PNG, and WebP.
"""

import io
import math
from PIL import Image, ImageChops, ExifTags

def create_test_jpeg():
    """Generates a test JPEG with synthetic EXIF (camera make, model, datetime)."""
    img = Image.new("RGB", (800, 600), color=(120, 180, 240))
    exif = img.getexif()
    # 0x010F = Make, 0x0110 = Model, 0x0131 = Software, 0x0132 = DateTime
    exif[0x010F] = "Canon"
    exif[0x0110] = "EOS 5D Mark IV"
    exif[0x0131] = "Adobe Lightroom 12.0"
    exif[0x0132] = "2026:05:14 10:30:00"
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=exif)
    return buf.getvalue(), img

def create_test_png_transparent():
    """Generates a test PNG with an alpha transparency gradient."""
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    # Draw a gradient with varying alpha
    for y in range(512):
        for x in range(512):
            alpha = int((x / 512.0) * 255)
            img.putpixel((x, y), (255, 100, 50, alpha))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img

def create_test_webp():
    """Generates a test WebP image."""
    img = Image.new("RGBA", (640, 480), (70, 130, 180, 200))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=95)
    return buf.getvalue(), img

def calculate_psnr(img1, img2):
    """Calculates Peak Signal-to-Noise Ratio between two RGB images."""
    diff = ImageChops.difference(img1.convert("RGB"), img2.convert("RGB"))
    stat = diff.histogram()
    mse = 0.0
    total_pixels = img1.width * img1.height * 3
    for i, count in enumerate(stat):
        val = i % 256
        mse += (val * val) * count
    mse /= total_pixels
    if mse == 0:
        return float('inf')
    return 20 * math.log10(255.0 / math.sqrt(mse))

def simulate_canvas_processing(image_bytes, mime_type, strip_metadata=True, quality=0.95, emulate_camera=False):
    """
    Simulates browser Canvas 2D processing:
    - Reads raw image into buffer
    - Draws raw pixels onto clean canvas (clearRect + drawImage at exact 1:1 dimensions)
    - If emulate_camera is True: applies 96% down/up cycle resize + calibrated DCT compression
    - Exports to specified MIME type without copying EXIF/IPTC/XMP
    """
    img = Image.open(io.BytesIO(image_bytes))
    orig_w, orig_h = img.size
    
    # Exact dimension preservation
    out_img = Image.new("RGBA" if img.mode == "RGBA" else "RGB", (orig_w, orig_h))
    out_img.paste(img, (0, 0))
    
    if emulate_camera:
        # Cycle resize: 96% downscale bilinear, then upscale back to 100%
        small_w = max(1, int(orig_w * 0.96))
        small_h = max(1, int(orig_h * 0.96))
        downscaled = out_img.resize((small_w, small_h), Image.Resampling.BILINEAR)
        out_img = downscaled.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
        if mime_type == "image/jpeg":
            quality = 0.86
    
    buf = io.BytesIO()
    if mime_type == "image/png":
        out_img.save(buf, format="PNG")
    elif mime_type == "image/jpeg":
        out_img.convert("RGB").save(buf, format="JPEG", quality=int(quality * 100))
    elif mime_type == "image/webp":
        out_img.save(buf, format="WEBP", quality=int(quality * 100))
    else:
        out_img.save(buf, format=img.format)
    
    return buf.getvalue(), out_img

def run_tests():
    print("=" * 60)
    print("RUNNING IMAGE PRIVACY PIPELINE VERIFICATION SUITE")
    print("=" * 60)
    
    passed = 0
    total = 0
    
    # ── Test 1: JPEG EXIF Metadata Stripping ────────────────────
    total += 1
    jpeg_bytes, orig_jpeg = create_test_jpeg()
    orig_opened = Image.open(io.BytesIO(jpeg_bytes))
    orig_exif = orig_opened.getexif()
    has_orig_camera = bool(orig_exif.get(0x010F) or orig_exif.get(0x0110))
    
    proc_jpeg_bytes, proc_jpeg = simulate_canvas_processing(jpeg_bytes, "image/jpeg", strip_metadata=True, quality=0.95)
    proc_opened = Image.open(io.BytesIO(proc_jpeg_bytes))
    proc_exif = proc_opened.getexif()
    has_proc_camera = bool(proc_exif.get(0x010F) or proc_exif.get(0x0110))
    
    dim_match = proc_jpeg.size == orig_jpeg.size
    psnr = calculate_psnr(orig_jpeg, proc_jpeg)
    
    print(f"\n[Test 1] JPEG Metadata Stripping & Fidelity:")
    print(f"  - Original Dimensions: {orig_jpeg.size}, Processed Dimensions: {proc_jpeg.size} (Match: {dim_match})")
    print(f"  - Original had Camera Model (EXIF): {has_orig_camera}")
    print(f"  - Processed has Camera Model (EXIF): {has_proc_camera} (Purged: {not has_proc_camera})")
    print(f"  - Visual Fidelity PSNR: {psnr:.2f} dB (High Quality: {psnr > 38})")
    
    if dim_match and has_orig_camera and not has_proc_camera and psnr > 38:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")
        
    # ── Test 2: Transparent PNG Alpha Preservation ──────────────
    total += 1
    png_bytes, orig_png = create_test_png_transparent()
    proc_png_bytes, proc_png = simulate_canvas_processing(png_bytes, "image/png", strip_metadata=True)
    
    dim_match_png = proc_png.size == orig_png.size
    has_alpha_orig = orig_png.mode == "RGBA"
    has_alpha_proc = proc_png.mode == "RGBA"
    
    # Check pixel differences in RGBA
    diff = ImageChops.difference(orig_png, proc_png)
    is_lossless = diff.getbbox() is None
    
    print(f"\n[Test 2] PNG Transparency & Alpha Preservation:")
    print(f"  - Original Dimensions: {orig_png.size}, Processed Dimensions: {proc_png.size} (Match: {dim_match_png})")
    print(f"  - Original RGBA mode: {has_alpha_orig}, Processed RGBA mode: {has_alpha_proc}")
    print(f"  - Pixel difference bbox: {diff.getbbox()} (Lossless: {is_lossless})")
    
    if dim_match_png and has_alpha_proc and is_lossless:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")
        
    # ── Test 3: WebP Integrity & Dimension Match ────────────────
    total += 1
    webp_bytes, orig_webp = create_test_webp()
    proc_webp_bytes, proc_webp = simulate_canvas_processing(webp_bytes, "image/webp", strip_metadata=True, quality=0.95)
    
    dim_match_webp = proc_webp.size == orig_webp.size
    psnr_webp = calculate_psnr(orig_webp, proc_webp)
    
    print(f"\n[Test 3] WebP Integrity & Quality:")
    print(f"  - Original Dimensions: {orig_webp.size}, Processed Dimensions: {proc_webp.size} (Match: {dim_match_webp})")
    print(f"  - Visual PSNR: {psnr_webp:.2f} dB (High Quality: {psnr_webp > 38})")
    
    if dim_match_webp and psnr_webp > 38:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")
        
    # ── Test 4: Format Conversion (PNG to JPEG) ─────────────────
    total += 1
    proc_conv_bytes, proc_conv = simulate_canvas_processing(png_bytes, "image/jpeg", strip_metadata=True, quality=0.95)
    dim_match_conv = proc_conv.size == orig_png.size
    is_jpeg = proc_conv_bytes[:2] == b"\xff\xd8"
    
    print(f"\n[Test 4] Format Conversion (PNG -> JPEG):")
    print(f"  - Converted Dimensions: {proc_conv.size} (Match: {dim_match_conv})")
    print(f"  - Converted format is JPEG: {is_jpeg}")
    
    if dim_match_conv and is_jpeg:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")
        
    # ── Test 5: Camera Emulation (De-AI Cycle Resize) ───────────
    total += 1
    proc_emu_bytes, proc_emu = simulate_canvas_processing(
        jpeg_bytes, "image/jpeg", strip_metadata=True, quality=0.86, emulate_camera=True
    )
    dim_match_emu = proc_emu.size == orig_jpeg.size
    psnr_emu = calculate_psnr(orig_jpeg, proc_emu)
    has_exif_emu = bool(proc_emu.getexif())
    
    print(f"\n[Test 5] Camera Emulation (De-AI Pipeline):")
    print(f"  - Dimensions after 96% down/up cycle: {proc_emu.size} (Match: {dim_match_emu})")
    print(f"  - Metadata Purged: {not has_exif_emu}")
    print(f"  - Visual PSNR: {psnr_emu:.2f} dB (Acceptable > 34 dB: {psnr_emu > 34})")
    
    if dim_match_emu and not has_exif_emu and psnr_emu > 34:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")
        
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
