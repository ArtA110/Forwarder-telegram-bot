FROM python:3.8-slim
EXPOSE 8000
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "telegrambot.py"]

