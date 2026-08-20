# Build from the repository root so shared contracts remain available:
# docker build -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SERVICE_NAME=backend-placeholder

COPY backend /app/backend
COPY contracts /app/contracts
COPY infra/placeholder_service.py /app/placeholder_service.py

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/healthz', timeout=2).read()"

CMD ["python", "/app/placeholder_service.py"]
