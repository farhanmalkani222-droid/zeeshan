FROM python:3.11-slim
WORKDIR /app
COPY . .
ENV DB_PATH=/data/bot.db PORT=8080
VOLUME /data
EXPOSE 8080
CMD ["python", "app.py"]
