import cv2
import json
from pathlib import Path
import csv

RAW_DIR = Path("raw")
COORD_FILE = Path("coordinates.json")
EXCLUDED_DIR = Path("excluded")
EXCLUDED_DIR.mkdir(parents=True, exist_ok=True)
EXCLUDED_CSV = EXCLUDED_DIR / "excluded_participants.csv"

# Load previously saved coordinates
if COORD_FILE.exists():
    coordinates = json.loads(COORD_FILE.read_text())
else:
    coordinates = {}

# Group videos by participant ID
participants = {}

for video_path in sorted(RAW_DIR.glob("*.mp4")):
    pid = video_path.stem.split("_")[0]
    participants.setdefault(pid, []).append(video_path)

WINDOW_NAME = "Select crop region"

for pid, videos in participants.items():

    # Skip participants with existing coordinates
    if pid in coordinates:
        print(f"Skipping {pid}: already recorded")
        continue

    video_path = videos[0]
    cap = cv2.VideoCapture(str(video_path))

    # Get the total number of frames
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Select the middle frame
    middle_frame = total_frames // 2

    # Move to the middle frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)

    # Read the selected frame
    success, frame = cap.read()
    cap.release()

    if not success:
        print(f"Cannot read {video_path}")
        continue

    print(f"\nParticipant: {pid}")
    print(f"Video: {video_path.name}")

    points = []

    def on_click(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 2:
                points.append((x, y))
                print(f"Selected: ({x}, {y})")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_NAME, on_click)

    while True:
        display = frame.copy()

        # Display selected points
        for point in points:
            cv2.circle(display, point, 5, (0, 0, 255), -1)

        # Display selected crop region
        if len(points) == 2:
            cv2.rectangle(
                display, points[0], points[1],
                (0, 255, 0), 2
            )

        cv2.imshow(WINDOW_NAME, display)
        key = cv2.waitKey(20) & 0xFF

        # Reset selection
        if key == ord("r"):
            points.clear()

         # Save coordinates
        elif key == ord("s") and len(points) == 2:

            x1, x2 = sorted([points[0][0], points[1][0]])
            y1, y2 = sorted([points[0][1], points[1][1]])

            if x1 == x2 or y1 == y2:
                print("Invalid crop region")
                continue

            coordinates[pid] = {
                "status": "crop",
                "top_left": [x1, y1],
                "bottom_right": [x2, y2]
            }

            COORD_FILE.write_text(
                json.dumps(coordinates, indent=4)
            )

            print(f"Saved coordinates for {pid}")
            break

        # Skip: participant's videos are unusable
        elif key == ord("n"):

            # Save the current frame
            image_path = EXCLUDED_DIR / f"{pid}.jpg"
            cv2.imwrite(str(image_path), frame)

            # Record exclusion reason
            reason = input(f"Reason for excluding {pid}: ").strip()

            # Save to JSON
            coordinates[pid] = {
                "status": "skip",
                "reason": reason,
                "screenshot": str(image_path),
                "source_video": video_path.name
            }

            COORD_FILE.write_text(
                json.dumps(coordinates, indent=4)
            )

            # Export all excluded participants to CSV
            with EXCLUDED_CSV.open("w", newline="", encoding="utf-8-sig") as f:

                writer = csv.writer(f)

                writer.writerow([
                    "Participant ID",
                    "Reason",
                    "Source video",
                    "Screenshot"
                ])

                for subject_id, config in sorted(coordinates.items()):
                    if config.get("status") == "skip":
                        writer.writerow([
                            subject_id,
                            config.get("reason", ""),
                            config.get("source_video", ""),
                            config.get("screenshot", "")
                        ])

            print(f"Excluded {pid}: {reason}")
            print(f"Screenshot saved: {image_path}")
            break

        # Ignore cropping: videos are already usable
        elif key == ord("i"):

            coordinates[pid] = {
                "status": "ignore"
            }

            COORD_FILE.write_text(
                json.dumps(coordinates, indent=4)
            )

            print(f"Ignored cropping for {pid}")
            break

        # Quit program
        elif key == ord("q"):
            cv2.destroyAllWindows()
            raise SystemExit

    cv2.destroyAllWindows()

print("Coordinate selection completed.")