FROM python:3.12-slim

WORKDIR /app

# Install deps first (cached layer if requirements unchanged)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the rest
COPY . .

# Railway sets the PORT env var dynamically.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]