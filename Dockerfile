# Dockerfile – AgriFlow Nexus Cloud Run image
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV STREAMLIT_SERVER_HEADLESS=true \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080
CMD streamlit run streamlit_app.py \
      --server.port $PORT \
      --server.headless true \
      --server.enableCORS false \
      --server.enableXsrfProtection false

