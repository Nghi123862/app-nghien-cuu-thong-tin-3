# syntax=docker/dockerfile:1
# Base: lightweight Ubuntu with Python 3.11 and Java 17
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

# Install system dependencies: Python, Java 17, X11, Xfce, VNC, noVNC, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    openjdk-17-jre-headless \
    ca-certificates curl wget git \
    xauth dbus-x11 xfce4 xfce4-goodies \
    tigervnc-standalone-server \
    novnc websockify \
    xfonts-base fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Spark 4.0.1
RUN wget https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz -O /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C /opt/ \
    && mv /opt/spark-4.0.1-bin-hadoop3 /opt/spark \
    && rm /tmp/spark.tgz

# Create user and workspace
RUN useradd -m -s /bin/bash ${USER_NAME}
WORKDIR ${APP_HOME}

# Copy project files (fixing the nested directory issue)
COPY app-check-thong-tin--feature-bigdata-pyspark-integration/app-check-thong-tin--feature-bigdata-pyspark-integration/. ${APP_HOME}/

# Create virtualenv and install Python dependencies
RUN python3 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Set Environment Variables for Java, Spark, and Python
ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64" \
    SPARK_HOME="/opt/spark" \
    PYSPARK_PYTHON="/opt/venv/bin/python" \
    PATH="/opt/venv/bin:/opt/spark/bin:${PATH}"

# Configure Spark defaults for Java 17 compatibility
RUN echo "spark.driver.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true" > ${SPARK_HOME}/conf/spark-defaults.conf \
    && echo "spark.executor.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true" >> ${SPARK_HOME}/conf/spark-defaults.conf

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
