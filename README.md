# KeyGate

Backend: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16. Frontend: React, TypeScript, Vite.
Vite przekierowuje `/api` na backend, więc wszystko działa pod jednym adresem.

## Uruchomienie

Potrzebne: Python 3.14, Node LTS, Docker.

```bash
cp .env.example .env
docker compose up -d

cd backend
python -m venv .venv
source .venv/Scripts/activate 
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

W drugim terminalu:

```bash
cd frontend
npm install
npm run dev
```

Strona: http://localhost:5173, API: http://localhost:8000/api/docs
