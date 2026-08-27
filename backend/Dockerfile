FROM python:3.11-slim

WORKDIR /app

# Install dependencies for psycopg2 and others
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

# Create a non-root user and switch to it
RUN useradd -m medibotuser && chown -R medibotuser:medibotuser /app
USER medibotuser

# Expose the application port
EXPOSE 8000

ENV PYTHONPATH=/app/backend

# Command to run Alembic migrations and then start FastAPI
CMD ["sh", "-c", "cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
