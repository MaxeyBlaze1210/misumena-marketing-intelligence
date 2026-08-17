import json
import subprocess
import tempfile
from pathlib import Path


def inspect_video(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height:"
            "stream_tags=rotate:"
            "stream_side_data=rotation",
            "-of", "json",
            path,
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    data = json.loads(result.stdout)

    streams = data.get("streams", [])

    if not streams:
        raise RuntimeError(
            "No video stream found."
        )

    stream = streams[0]

    rotation = None

    tags = stream.get("tags") or {}

    if "rotate" in tags:
        try:
            rotation = int(tags["rotate"])
        except (TypeError, ValueError):
            pass

    for item in stream.get("side_data_list", []):
        if "rotation" in item:
            try:
                rotation = int(item["rotation"])
            except (TypeError, ValueError):
                pass

    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "rotation": rotation,
    }


def prepare_video_for_youtube(
    source_path: str,
) -> tuple[str, bool]:
    """
    Normalize contradictory rotation metadata before
    uploading to YouTube.

    Returns:
        (path_to_upload, created_new_file)
    """

    info = inspect_video(source_path)

    width = info["width"]
    height = info["height"]
    rotation = info["rotation"]

    # Normal file: upload unchanged.
    if not rotation:
        return source_path, False

    suffix = Path(source_path).suffix or ".mp4"

    handle = tempfile.NamedTemporaryFile(
        prefix="mmi_youtube_normalized_",
        suffix=suffix,
        delete=False,
    )
    output_path = handle.name
    handle.close()

    try:
        # Do not auto-rotate the already portrait pixels.
        # Re-encode them exactly as stored and discard
        # the contradictory rotation metadata.
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-noautorotate",
                "-i", source_path,
                "-map_metadata", "-1",
                "-metadata:s:v:0", "rotate=0",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                output_path,
            ],
            check=True,
        )

        normalized = inspect_video(
            output_path
        )

        if normalized["rotation"]:
            raise RuntimeError(
                "YouTube video normalization did "
                "not remove rotation metadata."
            )

        if (
            normalized["width"] != width
            or normalized["height"] != height
        ):
            raise RuntimeError(
                "YouTube normalization changed "
                "video dimensions unexpectedly."
            )

        return output_path, True

    except Exception:
        Path(output_path).unlink(
            missing_ok=True
        )
        raise
