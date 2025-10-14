FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        VIRTUAL_ENV=/opt/venv

WORKDIR /srv/p4bot

# Install system build dependencies needed to build P4Python and other wheels
RUN apt-get update && \
        apt-get install -y --no-install-recommends \
        ca-certificates wget git build-essential python3-venv python3-dev libssl-dev swig openssh-client && \
        rm -rf /var/lib/apt/lists/*

# Create a lightweight Python virtual environment for the app and ensure pip is up-to-date
RUN python3 -m venv ${VIRTUAL_ENV} && \
        ${VIRTUAL_ENV}/bin/pip install --upgrade pip setuptools wheel

# Make sure the venv bin directory is on PATH for subsequent RUN steps and for the final image
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

# Copy requirements and install into the venv (isolated, avoids global pip warnings)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Do not attempt to copy local perforce secrets into the build context.
# Prefer mounting perforce config/ticket files into the container (P4CONFIG/P4TICKETS)
ENV P4PASSWD_FILE=/root/.p4tickets

# Copy the application code (mounted during dev via compose)
COPY app ./app

EXPOSE 8080

# Default command uses the venv python runtime
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app.server:app"]
