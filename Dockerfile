# Hugging Face Spaces (Docker) — free hosting, no credit card required.
FROM python:3.11-slim

WORKDIR /app
COPY . /app

# HF Spaces Docker containers must listen on port 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["python3", "backend/server.py"]
