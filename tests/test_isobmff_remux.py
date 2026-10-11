import io
import struct

def remux_mov_to_mp4(mov_bytes):
    """
    Pure ISOBMFF stream remuxer:
    1. Reads boxes from MOV file.
    2. Constructs standard MP4 'ftyp' box (isom / mp42).
    3. Relocates 'moov' before 'mdat' (faststart).
    4. Adjusts 32-bit chunk offsets ('stco') and 64-bit offsets ('co64') inside 'moov'.
    5. Returns valid MP4 bytes.
    """
    pos = 0
    total_len = len(mov_bytes)
    boxes = {}
    box_order = []
    
    while pos < total_len:
        if pos + 8 > total_len:
            break
        size = struct.unpack(">I", mov_bytes[pos:pos+4])[0]
        box_type = mov_bytes[pos+4:pos+8].decode("latin1", errors="ignore")
        
        box_data_start = pos + 8
        if size == 1: # 64-bit size
            size = struct.unpack(">Q", mov_bytes[pos+8:pos+16])[0]
            box_data_start = pos + 16
        elif size == 0:
            size = total_len - pos
            
        box_data = mov_bytes[box_data_start:pos+size]
        boxes[box_type] = box_data
        box_order.append((box_type, pos, size))
        pos += size

    if 'moov' not in boxes or 'mdat' not in boxes:
        raise ValueError("Invalid MOV file: missing moov or mdat box")

    # Create MP4 ftyp box (major: isom, minor: 0x200, brands: isom, iso2, mp41, mp42)
    ftyp_payload = b"isom" + struct.pack(">I", 0x200) + b"isomiso2mp41mp42"
    ftyp_box = struct.pack(">I", 8 + len(ftyp_payload)) + b"ftyp" + ftyp_payload

    # We want faststart: ftyp -> moov -> mdat
    moov_data = bytearray(boxes['moov'])
    mdat_data = boxes['mdat']

    # Calculate shift for chunk offsets:
    # In original MOV: mdat was at offset (len(ftyp) + len(wide) etc.)
    # In new MP4: mdat will be at offset (len(ftyp_box) + len(moov_box) + 8)
    new_mdat_offset = len(ftyp_box) + (8 + len(moov_data)) + 8

    # Find original mdat offset
    orig_mdat_offset = 0
    for b_type, b_pos, b_size in box_order:
        if b_type == 'mdat':
            orig_mdat_offset = b_pos + 8
            break

    offset_shift = new_mdat_offset - orig_mdat_offset

    # Adjust chunk offsets in moov (stco / co64 boxes)
    def patch_offsets(data, shift):
        p = 0
        while p < len(data) - 8:
            box_sz = struct.unpack(">I", data[p:p+4])[0]
            if box_sz < 8:
                p += 4
                continue
            b_typ = bytes(data[p+4:p+8])
            if b_typ == b"stco":
                # Version (1 byte), flags (3 bytes), entry_count (4 bytes)
                cnt = struct.unpack(">I", data[p+12:p+16])[0]
                entry_pos = p + 16
                for _ in range(cnt):
                    if entry_pos + 4 > len(data): break
                    old_off = struct.unpack(">I", data[entry_pos:entry_pos+4])[0]
                    new_off = max(0, old_off + shift)
                    data[entry_pos:entry_pos+4] = struct.pack(">I", new_off)
                    entry_pos += 4
            elif b_typ == b"co64":
                cnt = struct.unpack(">I", data[p+12:p+16])[0]
                entry_pos = p + 16
                for _ in range(cnt):
                    if entry_pos + 8 > len(data): break
                    old_off = struct.unpack(">Q", data[entry_pos:entry_pos+8])[0]
                    new_off = max(0, old_off + shift)
                    data[entry_pos:entry_pos+8] = struct.pack(">Q", new_off)
                    entry_pos += 8
            p += 1

    patch_offsets(moov_data, offset_shift)

    moov_box = struct.pack(">I", 8 + len(moov_data)) + b"moov" + bytes(moov_data)
    mdat_box = struct.pack(">I", 8 + len(mdat_data)) + b"mdat" + mdat_data

    return ftyp_box + moov_box + mdat_box

if __name__ == "__main__":
    with open("sample.mov", "rb") as f:
        mov = f.read()
    mp4 = remux_mov_to_mp4(mov)
    with open("sample_pure_js.mp4", "wb") as f:
        f.write(mp4)
    print("Successfully created sample_pure_js.mp4! Size:", len(mp4))
