import cv2
import numpy as np

width, height = 640, 360
fps = 30
duration_sec = 2
num_frames = fps * duration_sec

# QuickTime MOV codec: mp4v or avc1
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('sample.mov', fourcc, fps, (width, height))

for i in range(num_frames):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Warm background gradient
    frame[:, :] = (245, 248, 252) # Light cream/amber hue
    
    # Draw moving amber circle
    cx = int(80 + (i / num_frames) * (width - 160))
    offset = 40 * np.sin(i / 5.0)
    cy = int(height / 2 + offset)
    cv2.circle(frame, (cx, cy), 35, (0, 180, 245), -1) # Amber gold
    
    # Draw text
    cv2.putText(frame, "NanoMOV -> MP4 Fast Converter", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    cv2.putText(frame, f"Frame {i+1}/{num_frames} - 30 FPS", (60, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    
    out.write(frame)

out.release()
print("sample.mov successfully created!")
