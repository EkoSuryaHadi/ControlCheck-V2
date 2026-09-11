FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
RUN apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends ca-certificates openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api ./apps/api
EXPOSE 8080
CMD ["uvicorn", "controlcheck.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
