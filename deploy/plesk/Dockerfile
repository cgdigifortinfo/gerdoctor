FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=""
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8001 \
    LOCAL_STORAGE_ROOT=/var/lib/gerdoctor/uploads \
    TMPDIR=/tmp

WORKDIR /app/backend

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

COPY backend/ /app/backend/
COPY deploy/plesk/app.py /app/backend/plesk_app.py
COPY --from=frontend-builder /build/frontend/build/ /app/frontend/

RUN mkdir -p /var/lib/gerdoctor/uploads \
    && useradd --system --uid 10001 --create-home --home-dir /home/gerdoctor gerdoctor \
    && chown -R gerdoctor:gerdoctor /app /var/lib/gerdoctor /tmp

USER gerdoctor

EXPOSE 8001

CMD ["sh", "-c", "python -m uvicorn plesk_app:app --host 0.0.0.0 --port ${PORT}"]
