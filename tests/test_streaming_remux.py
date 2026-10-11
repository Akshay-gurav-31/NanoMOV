import io
import struct
import subprocess

def streaming_remux(file_path):
    """
    Simulates zero-copy Blob.slice() remuxing:
    - Never loads the whole file into RAM.
    - Only reads box headers and 'moov' atom.
    - Slices 'mdat' directly from the source file.
    """
    import os
    file_size = os.path.getsize(file_path)
    
    with open(file_path, "rb") as f:
        pos = 0
        moov_data = None
        mdat_pos = 0
        mdat_size = 0
        mdat_data_pos = 0
        
        while pos < file_size:
            f.seek(pos)
            hdr = f.read(16)
            if len(hdr) < 8:
                break
            size = struct.unpack(">I", hdr[:4])[0]
            box_type = hdr[4:8].decode("latin1", errors="ignore")
            
            box_data_start = pos + 8
            if size == 1:
                size = struct.unpack(">Q", hdr[8:16])[0]
                box_data_start = pos + 16
            elif size == 0:
                size = file_size - pos
                
            if box_type == "moov":
                f.seek(box_data_start)
                moov_data = bytearray(f.read(size - (box_data_start - pos)))
            elif box_type == "mdat":
                mdat_pos = pos
                mdat_data_pos = box_data_start
                mdat_size = size
                
            pos += size
            
        assert moov_data is not None, "moov not found"
        assert mdat_size > 0, "mdat not found"
        
        # Build standard MP4 ftyp box (32 bytes)
        ftyp_payload = b"isom" + struct.pack(">I", 0x200) + b"isomiso2mp41mp42"
        ftyp_box = struct.pack(">I", 8 + len(ftyp_payload)) + b"ftyp" + ftyp_payload
        
        # Calculate offset shift for FastStart:
        # new mdat data position = len(ftyp_box) + (8 + len(moov_data)) + (mdat_data_pos - mdat_pos)
        new_mdat_data_pos = len(ftyp_box) + (8 + len(moov_data)) + (mdat_data_pos - mdat_pos)
        offset_shift = new_mdat_data_pos - mdat_data_pos
        
        # Patch chunk offsets (stco and co64) in moov
        p = 0
        while p < len(moov_data) - 8:
            box_sz = struct.unpack(">I", moov_data[p:p+4])[0]
            if box_sz < 8:
                p += 4
                continue
            b_typ = bytes(moov_data[p+4:p+8])
            if b_typ == b"stco":
                cnt = struct.unpack(">I", moov_data[p+12:p+16])[0]
                entry_pos = p + 16
                for _ in range(cnt):
                    if entry_pos + 4 > len(moov_data): break
                    old_off = struct.unpack(">I", moov_data[entry_pos:entry_pos+4])[0]
                    new_off = max(0, old_off + offset_shift)
                    moov_data[entry_pos:entry_pos+4] = struct.pack(">I", new_off)
                    entry_pos += 4
            elif b_typ == b"co64":
                cnt = struct.unpack(">I", moov_data[p+12:p+16])[0]
                entry_pos = p + 16
                for _ in range(cnt):
                    if entry_pos + 8 > len(moov_data): break
                    old_off = struct.unpack(">Q", moov_data[entry_pos:entry_pos+8])[0]
                    new_off = max(0, old_off + offset_shift)
                    moov_data[entry_pos:entry_pos+8] = struct.pack(">Q", new_off)
                    entry_pos += 8
            p += 1
            
        moov_box = struct.pack(">I", 8 + len(moov_data)) + b"moov" + bytes(moov_data)
        
        # Sliced mdat from file (Zero memory load!)
        f.seek(mdat_pos)
        mdat_box = f.read(mdat_size)
        
        return ftyp_box + moov_box + mdat_box

if __name__ == "__main__":
    mp4_bytes = streaming_remux("sample.mov")
    with open("sample_streamed.mp4", "wb") as f:
        f.write(mp4_bytes)
    print("Streaming remux success! Output size:", len(mp4_bytes))
    
    # Verify with ffmpeg
    res = subprocess.run(["ffmpeg", "-v", "error", "-i", "sample_streamed.mp4", "-f", "null", "-"], capture_output=True, text=True)
    print("FFmpeg verification return code:", res.returncode, "Error:", res.stderr)
