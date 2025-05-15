FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install

CMD ["python", "twitch_bot.py"]
