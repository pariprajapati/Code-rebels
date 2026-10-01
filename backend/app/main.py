from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .db import DB
from .detector import Detector
from .ai import generate_document

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "duckdb" / "abhedya.duckdb"
WEB = ROOT / "frontend"

db = DB(DB_PATH)
detector = Detector(db)

app = FastAPI(title="Operation Abhedya-Chakra", version="1.0.0")

class DocumentRequest(BaseModel):
    account_id: str
    kind: str = "case_diary"

@app.get("/api/health")
def health():
    return {"status":"ok", "offline":True, "database":db.exists(), "version":"1.0.0"}

@app.get("/api/stats")
def stats():
    return db.stats()

@app.get("/api/search")
def search(q: str, limit: int = 20):
    if not q:
        return []
    return db.search_accounts(q, min(limit, 50))

@app.get("/api/account/{account_id}")
def account(account_id: str):
    data = db.account_summary(account_id)
    if not data:
        raise HTTPException(404, "Account not found")
    return data

@app.get("/api/account/{account_id}/transactions")
def transactions(account_id: str, limit: int = 200):
    return db.account_transactions(account_id, min(limit, 1000))

@app.get("/api/investigation/{account_id}")
def investigation(account_id: str, hops: int = 4):
    if not db.account_exists(account_id):
        raise HTTPException(404, "Account not found")
    return detector.investigate(account_id, max(1, min(hops, 4)))

@app.get("/api/risk/{account_id}")
def risk(account_id: str):
    if not db.account_exists(account_id):
        raise HTTPException(404, "Account not found")
    return detector.risk(account_id)

@app.post("/api/document")
def document(req: DocumentRequest):
    if not db.account_exists(req.account_id):
        raise HTTPException(404, "Account not found")
    evidence = detector.investigate(req.account_id, 4)
    return generate_document(evidence, req.kind)

app.mount("/assets", StaticFiles(directory=str(WEB / "assets")), name="assets")

@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
