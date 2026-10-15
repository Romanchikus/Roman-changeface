import shutil
import subprocess
from pathlib import Path

from fastapi import UploadFile

from app.shared.config import get_settings
from app.shared.errors import MediaRejected

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_RIFF = b"RIFF"
_WEBP = b"WEBP"


def safe_filename(name: str | None, fallback: str) -> str:
    base = Path(name or fallback).name.replace("\x00", "")
    cleaned = base.strip() or fallback
    return cleaned[:180]


def suffix_for(name: str, allowed: set[str], default: str) -> str:
    suffix = Path(name).suffix.lower()
    return suffix if suffix in allowed else default


def save_upload(upload: UploadFile, dest: Path, max_bytes: int, label: str) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with dest.open("wb") as handle:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise MediaRejected(
                        413,
                        "file_too_large",
                        f"{label} is larger than {max_bytes / (1024 * 1024):.0f} MB.",
                    )
                handle.write(chunk)
    except MediaRejected:
        dest.unlink(missing_ok=True)
        raise
    if total == 0:
        dest.unlink(missing_ok=True)
        raise MediaRejected(400, "empty_file", f"{label} is empty.")
    return total


def assert_image(path: Path) -> None:
    header = path.read_bytes()[:16]
    is_png = header.startswith(_PNG)
    is_jpeg = header.startswith(_JPEG)
    is_webp = header.startswith(_RIFF) and header[8:12] == _WEBP
    if not (is_png or is_jpeg or is_webp):
        raise MediaRejected(400, "invalid_image", "Source image must be JPEG, PNG, or WebP.")


def probe_duration_seconds(path: Path) -> float:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MediaRejected(500, "ffprobe_missing", "ffprobe is not installed.") from exc
    if proc.returncode != 0:
        raise MediaRejected(400, "invalid_video", "Could not read the target video.")
    try:
        duration = float(proc.stdout.strip())
    except ValueError as exc:
        raise MediaRejected(400, "invalid_video", "Could not read the target video duration.") from exc
    limit = get_settings().max_video_duration_sec
    if duration <= 0:
        raise MediaRejected(400, "invalid_video", "Target video duration must be greater than zero.")
    if duration > limit:
        raise MediaRejected(
            400,
            "video_too_long",
            f"Video is {duration:.1f}s. The limit is {limit:.0f}s.",
        )
    return duration


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
