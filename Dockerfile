FROM python:3.10-slim

WORKDIR /app
COPY . .

# ✅ добавляем недостающие библиотеки
RUN apt-get update && apt-get install -y wget gnupg ca-certificates fonts-liberation libasound2 libatk1.0-0 \
libatk-bridge2.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
libxdamage1 libxrandr2 libgbm1 libxkbcommon0 libgtk-3-0 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install

CMD ["python", "twitch_bot.py"]
