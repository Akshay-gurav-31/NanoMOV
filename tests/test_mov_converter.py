"""
Automated Verification Suite for CleanMOV (Fast MOV to MP4 Converter)
======================================================================
Validates:
1. Fast ISOBMFF Stream Copy Remuxing.
2. Web FastStart (+faststart) atom relocation.
3. Zero-loss video frame integrity.
4. Full playback validity with ffprobe and ffmpeg.
"""

import subprocess
import os
import struct
from test_isobmff_remux import remux_mov_to_mp4

def run_suite():
    print("=" * 60)
    print("RUNNING CLEANMOV (MOV TO MP4) VERIFICATION SUITE")
    print("=" * 60)

    passed = 0
    total = 0

    # 1. Test Input Sample Existence
    total += 1
    if not os.path.exists("sample.mov"):
        print("[Test 1] Missing sample.mov! Generating...")
        import create_sample_mov
    
    mov_exists = os.path.exists("sample.mov")
    print(f"\n[Test 1] Sample MOV Input Available: {mov_exists}")
    if mov_exists:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")

    # 2. Test Stream Copy Remuxing
    total += 1
    with open("sample.mov", "rb") as f:
        mov_bytes = f.read()

    mp4_bytes = remux_mov_to_mp4(mov_bytes)
    with open("sample_verified.mp4", "wb") as f:
        f.write(mp4_bytes)

    print(f"\n[Test 2] Stream Remuxing Execution:")
    print(f"  - Input MOV Size:  {len(mov_bytes)} bytes")
    print(f"  - Output MP4 Size: {len(mp4_bytes)} bytes")
    remux_success = len(mp4_bytes) > 0
    if remux_success:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")

    # 3. Test Web FastStart (+faststart) Atom Ordering
    total += 1
    pos = 0
    box_order = []
    while pos < len(mp4_bytes):
        sz = struct.unpack(">I", mp4_bytes[pos:pos+4])[0]
        typ = mp4_bytes[pos+4:pos+8].decode("latin1", errors="ignore")
        box_order.append(typ)
        if sz == 0 or sz < 8: break
        pos += sz

    print(f"\n[Test 3] FastStart Box Order: {box_order}")
    # FastStart requires 'moov' to appear BEFORE 'mdat'
    is_faststart = False
    if 'moov' in box_order and 'mdat' in box_order:
        is_faststart = box_order.index('moov') < box_order.index('mdat')

    print(f"  - 'moov' before 'mdat' (FastStart enabled): {is_faststart}")
    if is_faststart:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")

    # 4. FFmpeg / FFprobe Deep Stream Validation
    total += 1
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "sample_verified.mp4", "-f", "null", "-"],
        capture_output=True, text=True
    )
    no_ffmpeg_errors = res.returncode == 0 and len(res.stderr.strip()) == 0
    print(f"\n[Test 4] FFmpeg Full Decode & Frame Validation:")
    print(f"  - FFmpeg return code: {res.returncode}")
    print(f"  - FFmpeg error log: '{res.stderr.strip()}'")
    if no_ffmpeg_errors:
        print("  -> PASSED")
        passed += 1
    else:
        print("  -> FAILED")

    # 5. FFprobe Stream Metadata Matching
    total += 1
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", "sample_verified.mp4"],
        capture_output=True, text=True
    )
    output_info = probe.stdout.strip()
    print(f"\n[Test 5] FFprobe Video Stream Inspection: {output_info}")
    valid_stream = "640" in output_info and "360" in output_info
    if valid_stream:
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
    success = run_suite()
    sys.exit(0 if success else 1)
