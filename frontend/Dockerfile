# Build from the repository root so the static demo and its fixtures share one context:
# docker build -f frontend/Dockerfile .
FROM nginx:1.27-alpine

COPY frontend/demo /usr/share/nginx/html
COPY frontend/fixtures /usr/share/nginx/html/fixtures
COPY infra/frontend-nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget --quiet --output-document=- http://127.0.0.1/healthz | grep --quiet '^ok$'
