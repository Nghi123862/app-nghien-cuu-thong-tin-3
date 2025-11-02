# syntax=docker/dockerfile:1

# --- Builder Stage ---
# Used to install dependencies and build artifacts, keeping the final image small.
FROM ubuntu:22.04 AS builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create and populate Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Pre-load dependencies and AI model
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY preload_model.py .
RUN python preload_model.py


# --- Final Stage ---
# The final, lean image for running the application.
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

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-tk \
    openjdk-17-jre-headless \
    xauth dbus-x11 xfce4 xfce4-goodies \
    tigervnc-standalone-server \
    novnc websockify \
    xfonts-base fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash ${USER_NAME}

# Copy artifacts from the builder stage
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/huggingface_cache ${APP_HOME}/huggingface_cache

# Set Environment Variables for Java 17 and Python
ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64" \
    PYSPARK_PYTHON="/opt/venv/bin/python" \
    PATH="/opt/venv/bin:${PATH}"

# Set up the application directory
WORKDIR ${APP_HOME}
COPY . ${APP_HOME}/
COPY --chown=${USER_NAME}:${USER_NAME} docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Create lightweight Xfce session and set permissions
RUN mkdir -p ${USER_HOME}/.vnc \
    && echo -e '#!/bin/bash\n\
unset SESSION_MANAGER\n\
unset DBUS_SESSION_BUS_ADDRESS\n\
/usr/bin/startxfce4 &\n\
sleep 5\n\
cd /app\n\
/opt/venv/bin/python /app/app.py' > ${USER_HOME}/.vnc/xstartup \
    && chmod +x ${USER_HOME}/.vnc/xstartup \
    && chown -R ${USER_NAME}:${USER_NAME} ${USER_HOME}

# Expose VNC and noVNC ports
EXPOSE ${VNC_PORT} ${NOVNC_PORT}

USER ${USER_NAME}

# Default command launches VNC server, noVNC and the Tkinter app
CMD ["/usr/local/bin/start.sh"]
