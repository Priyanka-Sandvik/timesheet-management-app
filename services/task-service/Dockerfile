# Build from the REPO ROOT (not this directory) so the build context includes
# ../../shared/py-common:
#   docker build -f services/task-service/Dockerfile -t task-service .
#
# requirements.txt's `-e ../../shared/py-common` line is for local dev venvs only (relative
# to services/task-service/ on disk) and does not resolve inside the Docker build context, so
# it is installed explicitly below and stripped from requirements.txt before the rest install.
FROM python:3.12-slim AS base

WORKDIR /build
COPY shared/py-common ./shared/py-common
RUN pip install --no-cache-dir ./shared/py-common

COPY services/task-service/requirements.txt ./services/task-service/requirements.txt
RUN grep -v '^-e ' services/task-service/requirements.txt > services/task-service/requirements.docker.txt \
    && pip install --no-cache-dir -r services/task-service/requirements.docker.txt

COPY services/task-service/app ./services/task-service/app

WORKDIR /build/services/task-service

ENV PORT=8002
EXPOSE 8002

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002}"]
