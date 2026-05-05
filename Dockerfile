# Build stage 
FROM python:3.12-slim AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage 
FROM python:3.12-slim

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ .

# Ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Environment defaults (overridden by docker-compose)
ENV MODE=stable \
    APP_VERSION=1.0.0 \
    APP_PORT=3000

EXPOSE 3000

# Drop all capabilities at runtime via docker-compose — image just sets entrypoint
CMD ["python", "main.py"]