FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Audit log volume mount point
VOLUME ["/app/data"]

EXPOSE 8010

CMD ["python", "-m", "app.main"]
