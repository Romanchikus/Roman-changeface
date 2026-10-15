#!/bin/sh
set -eu

python facefusion.py headless-run \
  -s girl.jpg \
  -t input.mp4 \
  -o test/output.mp4 \
  --processors face_swapper \
  --execution-providers cuda \
  --face-detector-model retinaface \
  --face-detector-score 0.3 \
  --face-selector-mode many \
  --output-audio-volume 100

mixed="$(mktemp /tmp/facefusion-output.XXXXXX.mp4)"
ffmpeg -y \
  -i test/output.mp4 \
  -i input.mp4 \
  -map 0:v:0 \
  -map 1:a:0 \
  -c:v copy \
  -c:a copy \
  -shortest \
  "$mixed"
mv "$mixed" test/output.mp4
chown "${HOST_UID:-1000}:${HOST_GID:-1000}" test test/output.mp4
chmod 775 test
chmod 664 test/output.mp4
