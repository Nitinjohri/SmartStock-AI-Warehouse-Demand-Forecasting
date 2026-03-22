FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Prophet + PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc g++ \
    libpq-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY ./backend ./backend

# Wait for PostgreSQL to be ready before starting
EXPOSE 8000

CMD ["python","-m","uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]