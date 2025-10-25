#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=${DISPLAY:-:1}
export VNC_PORT=${VNC_PORT:-5901}
export NOVNC_PORT=${NOVNC_PORT:-6080}
export RESOLUTION=${RESOLUTION:-1366x768}

# Clean up stale VNC and X server files that might prevent startup
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
mkdir -p "$HOME/.vnc"

# Start VNC server in the foreground. It will run xstartup.
echo "Starting VNC server on display ${DISPLAY}..."
vncserver "$DISPLAY" -geometry "$RESOLUTION" -SecurityTypes None -alwaysshared -fg &
VNC_PID=$!

# Start the noVNC WebSocket proxy
echo "Starting noVNC proxy on port ${NOVNC_PORT}..."
websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:"$VNC_PORT" &
WEBSOCK_PID=$!

echo "----------------------------------------------------"
echo "VNC server and noVNC proxy are running."
echo "You can now connect to the application in your browser:"
echo "URL: http://localhost:6080/"
echo "----------------------------------------------------"

# Wait for the VNC server to exit
wait $VNC_PID
# If VNC server exits, also stop the websockify proxy
kill $WEBSOCK_PID
