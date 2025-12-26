# Базовый образ
FROM python:3.11-slim

# Отключаем интерактивные вопросы apt
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости (исправленный пакет!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libgdk-pixbuf-2.0-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libxkbcommon0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости Python
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Команда запуска бота
CMD ["python", "bot.py"]
