# Build from the repository root so the image can copy contracts/:
# docker build -f ai-service/Dockerfile .
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    PORT=8001 \
    SERVICE_NAME=ai-service-placeholder

RUN apt-get update \
  && apt-get install --no-install-recommends --yes ca-certificates python3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ai-service /app/ai-service
COPY contracts /app/contracts
COPY infra/placeholder_service.py /app/placeholder_service.py

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8001') + '/healthz', timeout=2).read()"

CMD ["python3", "/app/placeholder_service.py"]
