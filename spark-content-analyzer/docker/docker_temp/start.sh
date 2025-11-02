#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=${DISPLAY:-:1}
export VNC_PORT=${VNC_PORT:-5901}
export NOVNC_PORT=${NOVNC_PORT:-6080}
export RESOLUTION=${RESOLUTION:-1366x768}

mkdir -p "$HOME/.vnc"

vncserver "$DISPLAY" -geometry "$RESOLUTION" -SecurityTypes None || true

websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:"$VNC_PORT" &

sleep 2

if ! pgrep -x xfce4-session >/dev/null; then
  startxfce4 &
fi

cd /app
python app.py