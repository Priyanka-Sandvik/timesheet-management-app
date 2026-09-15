# Build from the REPO ROOT so the build context includes shared/py-common:
#   docker build -f services/timelog-service/Dockerfile -t timelog-service .
#
# requirements.txt's `-e ../../shared/py-common` line is for local dev venvs only (relative
# to services/timelog-service/ on disk) and does not resolve inside the Docker build context,
# so it is installed explicitly below and stripped from requirements.txt before the rest install.
FROM python:3.12-slim

WORKDIR /app

COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

COPY services/timelog-service/requirements.txt /app/requirements.txt
RUN grep -v '^-e ' /app/requirements.txt > /app/requirements.docker.txt \
    && pip install --no-cache-dir -r /app/requirements.docker.txt

COPY services/timelog-service /app

ENV PORT=8003
EXPOSE 8003

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
