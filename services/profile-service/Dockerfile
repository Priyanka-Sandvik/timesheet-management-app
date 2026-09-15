# Build from the REPO ROOT (not this directory) because this service depends on the local
# path package `shared/py-common`, which must be inside the Docker build context:
#
#   docker build -f services/profile-service/Dockerfile -t profile-service .
#
# (run from timesheet-management-app/, the repo root)
#
# This Dockerfile copies shared/py-common into the image and `pip install`s it in
# editable-equivalent form (a normal, non-editable install is used here since editable
# installs of a path that no longer exists at runtime don't make sense in a container;
# requirements.txt's `-e ../../shared/py-common` line is for local dev venvs only and is
# stripped out below before installing inside the image).

FROM python:3.12-slim AS base

WORKDIR /build

# Copy the shared package first (better Docker layer caching) and install it as a normal
# dependency (not editable -- editable installs need the source path to persist, which it
# does here since we COPY it into /build/shared/py-common, but a plain install is simpler
# and equally correct for a container image).
COPY shared/py-common /build/shared/py-common
RUN pip install --no-cache-dir /build/shared/py-common

# Install profile-service's own dependencies, excluding the `-e ../../shared/py-common`
# line (already installed above from the correct in-container path).
COPY services/profile-service/requirements.txt /build/requirements.txt
RUN grep -v '^-e ' /build/requirements.txt > /build/requirements.docker.txt \
    && pip install --no-cache-dir -r /build/requirements.docker.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

COPY services/profile-service/app /app/app

# Container Apps sets PORT at runtime; default to 8001 for local `docker run`.
ENV PORT=8001

EXPOSE 8001

# Shell form so ${PORT} expands at container start (Azure Container Apps convention).
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
