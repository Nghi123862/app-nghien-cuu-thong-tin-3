# syntax=docker/dockerfile:1
# Base: lightweight Ubuntu with Python 3.11
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    APP_HOME=/app \
    DISPLAY=:1 \
    VNC_PORT=5901 \
    NOVNC_PORT=6080 \
    RESOLUTION=1280x800 \
    USER_NAME=developer \
    USER_HOME=/home/developer

# Install system dependencies: Python, Java (for PySpark), X11, Xfce, VNC, noVNC, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    openjdk-11-jre-headless \
    ca-certificates curl wget git \
    xauth dbus-x11 xfce4 xfce4-goodies \
    tigervnc-standalone-server \
    novnc websockify \
    xfonts-base fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Create user and workspace
RUN useradd -m -s /bin/bash ${USER_NAME}
WORKDIR ${APP_HOME}

# Copy project files
COPY app-check-thong-tin--feature-bigdata-pyspark-integration/ ${APP_HOME}/

# Create virtualenv and install Python dependencies
RUN python3 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

ENV PATH="/opt/venv/bin:${PATH}" \
    JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"

# Create lightweight Xfce session and VNC startup script
RUN mkdir -p ${USER_HOME}/.vnc \
    && echo "#!/bin/bash\nstartxfce4 &" > ${USER_HOME}/.vnc/xstartup \
    && chmod +x ${USER_HOME}/.vnc/xstartup \
    && chown -R ${USER_NAME}:${USER_NAME} ${USER_HOME}

# Startup scripts
COPY --chown=${USER_NAME}:${USER_NAME} docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Expose VNC and noVNC ports
EXPOSE ${VNC_PORT} ${NOVNC_PORT}

USER ${USER_NAME}

# Default command launches VNC server, noVNC and the Tkinter app
CMD ["/usr/local/bin/start.sh"]
