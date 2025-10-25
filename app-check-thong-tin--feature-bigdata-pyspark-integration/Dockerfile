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

# Install Spark 4.0.1
RUN wget https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz -O /tmp/spark.tgz \
    && mkdir -p /opt/spark \
    && tar -xzf /tmp/spark.tgz -C /opt/spark --strip-components=1 \
    && rm /tmp/spark.tgz

# Create and populate Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt


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
COPY --from=builder /opt/spark /opt/spark

# Set Environment Variables for Java, Spark, and Python
ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64" \
    SPARK_HOME="/opt/spark" \
    PYSPARK_PYTHON="/opt/venv/bin/python" \
    PATH="/opt/venv/bin:/opt/spark/bin:${PATH}"

# Configure Spark defaults for Java 17 compatibility
RUN echo "spark.driver.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true" > ${SPARK_HOME}/conf/spark-defaults.conf \
    && echo "spark.executor.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true" >> ${SPARK_HOME}/conf/spark-defaults.conf

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
