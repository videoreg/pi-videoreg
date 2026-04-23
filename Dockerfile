FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-netifaces \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем зависимости отдельным слоем для кэширования
COPY requirements.txt .
RUN python3 -m venv --system-site-packages .venv && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
