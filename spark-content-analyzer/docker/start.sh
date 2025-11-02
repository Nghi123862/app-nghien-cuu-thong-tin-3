#!/usr/bin/env bash
set -euo pipefail

# Ensure environment
export DISPLAY=${DISPLAY:-:1}
export VNC_PORT=${VNC_PORT:-5901}
export NOVNC_PORT=${NOVNC_PORT:-6080}
export RESOLUTION=${RESOLUTION:-1280x800}

# Start VNC server (no password)
mkdir -p "$HOME/.vnc"
# Generate a random password file just in case (not used by default)
if [ ! -f "$HOME/.vnc/passwd" ]; then
  x11vnc -storepasswd "" "$HOME/.vnc/passwd" >/dev/null 2>&1 || true
fi

# Start TigerVNC server
vncserver "$DISPLAY" -geometry "$RESOLUTION" -SecurityTypes None || true

# Start noVNC
websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:"$VNC_PORT" &

# Wait a moment for VNC to initialize
sleep 2

# Launch desktop session if not already
if ! pgrep -x xfce4-session >/dev/null; then
  startxfce4 &
fi

cd /app
# Run the Tkinter application
python app.py
