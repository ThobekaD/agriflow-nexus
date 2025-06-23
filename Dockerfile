# Dockerfile – AgriFlow Nexus Cloud Run image
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential python3-dev \
  && pip install --no-cache-dir -r requirements.txt \
  && apt-get purge -y build-essential && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python","main.py"]

