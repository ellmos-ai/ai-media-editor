#!/bin/sh
# Regenerate the synthetic, rights-free end-to-end fixture (task 1242).
# Needs: ffmpeg/ffprobe, shasum and a python with espeakng-loader==0.2.4 (PYTHON, default python3). Every input is generated here; no recording is used.
set -eu
cd "$(dirname "$0")"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"${PYTHON:-python3}" espeak_tts.py "$tmp/take1.wav" "This is a synthetic test clip for the media editor."
"${PYTHON:-python3}" espeak_tts.py "$tmp/take2.wav" "The second take starts after a clear pause."
ffmpeg -hide_banner -loglevel error -y -i "$tmp/take1.wav" -f lavfi -t 1.5 -i anullsrc=r=22050:cl=mono \
  -i "$tmp/take2.wav" -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]" -map "[a]" "$tmp/speech.wav"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$tmp/speech.wav")
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=320x180:rate=25" -i "$tmp/speech.wav" \
  -t "$dur" -map 0:v -map 1:a -c:v libx264 -crf 30 -pix_fmt yuv420p -c:a aac -b:a 64k -ac 1 \
  -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact -movflags +faststart fixture.mp4
shasum -a 256 fixture.mp4
