FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    P4_SCRIPT_ROOT=/scripts

WORKDIR /srv/p4bot

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates wget build-essential python3-dev libssl-dev swig && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install P4Python via pip (Helix API). This requires build deps above.
RUN pip install --no-cache-dir P4Python || true

# Optional: provide a p4 CLI binary URL at build time using build-arg P4_CLI_URL
ARG P4_CLI_URL=""
RUN if [ -n "$P4_CLI_URL" ]; then \
            echo "Downloading p4 from $P4_CLI_URL" && \
            wget -O /usr/local/bin/p4 "$P4_CLI_URL" && \
            chmod +x /usr/local/bin/p4 || (echo "Failed to fetch p4 from $P4_CLI_URL" && false); \
        else \
            echo "P4_CLI_URL not provided; p4 client will not be installed in the image"; \
        fi

# If a local asset matching the build arch exists, copy it into the image.
ARG TARGETARCH
# Copy any provided asset binaries into a temp location and pick the right one
RUN mkdir -p /opt/p4-assets || true
COPY assets/p4 /opt/p4-assets/p4
COPY assets/p4-ARM /opt/p4-assets/p4-ARM
RUN if [ "${TARGETARCH}" = "arm64" ] && [ -f /opt/p4-assets/p4-ARM ]; then \
            cp /opt/p4-assets/p4-ARM /usr/local/bin/p4; \
        elif [ -f /opt/p4-assets/p4-${TARGETARCH} ]; then \
            cp /opt/p4-assets/p4-${TARGETARCH} /usr/local/bin/p4; \
        elif [ -f /opt/p4-assets/p4 ]; then \
            cp /opt/p4-assets/p4 /usr/local/bin/p4; \
        fi && chmod +x /usr/local/bin/p4 || true

# Do not attempt to copy local perforce secrets into the build context.
# Prefer mounting `/perforce` (or `perforce/secrets/p4passwd`) at runtime.
# If you intentionally want to embed secrets, place them inside the build
# context and adjust this Dockerfile accordingly. For typical dev use we
# read the password from the mounted `/scripts/secrets/p4passwd`.
ENV P4PASSWD_FILE=/scripts/secrets/p4passwd

COPY app ./app

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app.server:app"]
