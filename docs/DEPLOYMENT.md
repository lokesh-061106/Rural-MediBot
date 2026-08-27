# M7 Deployment Guide

## Prerequisites
- Docker & Docker Compose
- Verified Medical Knowledge Documents (See DATA_READINESS.md)
- Verified Facility Data JSON (See DATA_READINESS.md)
- Valid Groq API Key

## Setup Steps
1. **Clone & Configuration**
   ```bash
   git clone https://github.com/lokesh-061106/Rural-MediBot.git
   cp .env.example .env
   ```
2. **Inject Secrets**
   Edit `.env` and fill in `JWT_SECRET_KEY`, `DB_PASSWORD`, `GROQ_API_KEY`.
3. **Data Ingestion**
   Place verified documents in `backend/data/documents`. Run the ingestion scripts:
   ```bash
   docker-compose run backend python app/knowledge/ingest.py
   docker-compose run backend python app/knowledge/facility_ingest.py path/to/facilities.json
   ```
4. **Launch Application**
   ```bash
   docker-compose up -d --build
   ```
5. **Verify Readiness**
   ```bash
   curl -f http://localhost:8000/ready
   ```

## CI/CD 
GitHub Actions automatically executes `pytest` and Next.js builds on every commit to the `main` branch. Broken commits will block deployment.

## M7 FINAL STATUS
**BLOCKED — EXTERNAL DATA/INFRASTRUCTURE REQUIRED**
Do not authorize clinical deployment until authoritative medical protocols and verified facility databases have been provided by official governance.

