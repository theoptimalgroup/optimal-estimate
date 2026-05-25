FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x startup.sh scripts/deploy-migrate.sh
RUN mkdir -p /app/storage/pdfs

ENV PORT=8000
ENV WEB_CONCURRENCY=2
ENV PYTHONUNBUFFERED=1
ENV RUN_SEED=false

EXPOSE 8000

# Azure App Service: set startup command to ./startup.sh
CMD ["/bin/bash", "./startup.sh"]
