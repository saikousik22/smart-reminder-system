FROM python:3.12-slim

# ffmpeg is required for audio transcoding
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fix case-sensitivity: Windows creates 'Versions', Linux needs 'versions'
RUN if [ -d alembic/Versions ] && [ ! -d alembic/versions ]; then \
    cp -r alembic/Versions alembic/versions; \
    fi

RUN mkdir -p uploads

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
