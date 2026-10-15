#!/bin/sh
set -eu

extra=""
for dir in /app/.venv/lib/python*/site-packages/nvidia/*/lib; do
  if [ -d "$dir" ]; then
    extra="${extra:+$extra:}$dir"
    if [ -e "$dir/libcudnn.so.9" ] && [ ! -e "$dir/libcudnn.so" ]; then
      ln -s libcudnn.so.9 "$dir/libcudnn.so"
    fi
  fi
done

if [ -n "$extra" ]; then
  export LD_LIBRARY_PATH="${extra}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

set +u
. /app/.venv/bin/activate
set -u
python - <<'PY'
import socket
import time
from urllib.parse import urlparse

from app.shared.config import get_settings

settings = get_settings()
print(settings.database_url)
host = urlparse(settings.database_url).hostname
if host:
    last_error = None
    for _ in range(settings.db_connect_attempts):
        try:
            socket.getaddrinfo(host, None)
            print("database host reachable")
            break
        except OSError as exc:
            last_error = exc
            time.sleep(0.5)
    else:
        raise SystemExit(f"database host not reachable: {host}: {last_error}")
PY
(cd /app && alembic upgrade head)

exec "$@"
