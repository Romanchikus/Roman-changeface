import subprocess
from pathlib import Path

from app.shared.config import get_settings


def thumbnail_file(media_id: int) -> Path:
    return Path(get_settings().storage_dir) / "thumbnails" / f"{media_id}.jpg"


def write_thumbnail(source: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=320:-2",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        return False
    return True
