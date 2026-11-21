import subprocess
import json
from pathlib import Path

RAW_DIR = Path("raw")
OUTPUT_DIR = Path("cropped")
COORD_FILE = Path("coordinates.json")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

coordinates = json.loads(COORD_FILE.read_text())


def crop_video(input_path, output_path, top_left, bottom_right):

    x1, y1 = top_left
    x2, y2 = bottom_right

    width = x2 - x1
    height = y2 - y1

    # Ensure even dimensions for H.264 encoding
    width -= width % 2
    height -= height % 2

    if width <= 0 or height <= 0:
        raise ValueError("Invalid crop coordinates")

    command = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", f"crop={width}:{height}:{x1}:{y1}:exact=1",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-an",
        "-n",
        str(output_path)
    ]

    subprocess.run(command, check=True)

# copy video without sound
def copy_video(input_path, output_path):
    command = [
        "ffmpeg",
        "-i", str(input_path),
        "-map", "0:v:0",
        "-c:v", "copy",
        "-an",
        "-n",
        str(output_path)
    ]

    subprocess.run(command, check=True)

for video_path in sorted(RAW_DIR.glob("*.mp4")):

    pid = video_path.stem.split("_")[0]

    # Participant has not yet been reviewed
    if pid not in coordinates:
        print(f"Skipping {video_path.name}: not reviewed")
        continue

    config = coordinates[pid]

    # Default to crop for compatibility with old JSON records
    status = config.get("status", "crop")

    output_path = OUTPUT_DIR / video_path.name

    # Exclude unusable videos
    if status == "skip":
        print(f"Excluded {video_path.name}")
        continue

    # Skip previously processed videos
    if output_path.exists():
        print(f"Skipping {video_path.name}: already processed")
        continue

    # Copy directly without cropping
    if status == "ignore":
        copy_video(video_path, output_path)
        print(f"Copied {video_path.name}")
        continue

    # Crop video
    if status == "crop":

        top_left = config["top_left"]
        bottom_right = config["bottom_right"]

        print(f"Cropping {video_path.name}")

        try:
            crop_video(
                input_path=video_path,
                output_path=output_path,
                top_left=top_left,
                bottom_right=bottom_right
            )
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Failed to crop {video_path.name}: {e}")

print("Video processing completed.")