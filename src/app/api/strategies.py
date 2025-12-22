from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid

from src.database.connect_db import SessionLocal
from src.database import crud
from src.database.models import RetrievalStrategy
from src.app.options.query import answer

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class StrategyCreate(BaseModel):
    name: str
    initial_top_k: int = 10
    rerank_top_k: int = 5
    score_threshold: Optional[float] = None
    description: Optional[str] = None

class StrategyResponse(BaseModel):
    id: str
    name: str
    initial_top_k: int
    rerank_top_k: int
    score_threshold: Optional[float]
    description: Optional[str]

    class Config:
        from_attributes = True

class TestStrategyRequest(BaseModel):
    query: str
    initial_top_k: int = 10
    rerank_top_k: int = 5
    score_threshold: Optional[float] = None

@router.post("/", response_model=StrategyResponse)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    # Check name unique
    existing_strategies = crud.get_all_strategies(db) # Naive check, but ok for now
    if any(s.name == strategy.name for s in existing_strategies):
         raise HTTPException(status_code=400, detail="Strategy name already exists")

    id = str(uuid.uuid4())
    return crud.create_strategy(
        db, 
        id, 
        strategy.name, 
        strategy.initial_top_k, 
        strategy.rerank_top_k, 
        strategy.score_threshold, 
        strategy.description
    )

@router.get("/", response_model=List[StrategyResponse])
def get_strategies(db: Session = Depends(get_db)):
    return crud.get_all_strategies(db)

@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: str, db: Session = Depends(get_db)):
    success = crud.delete_strategy(db, strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"message": "Deleted"}

@router.post("/test")
def test_strategy(req: TestStrategyRequest):
    """
    Test a strategy configuration.
    Returns the chunks (sources) directly.
    """
    # Create a temporary config object
    retrieval_config = {
        "initial_top_k": req.initial_top_k,
        "rerank_top_k": req.rerank_top_k,
        "score_threshold": req.score_threshold
    }
    
    # Call answer with config
    # We need to update answer() to accept retrieval_config
    # Ideally answer() should return structured data including chunks
    
    # Note: query.py's answer() currently returns (reply, sources, chunks)
    # response, sources, chunks = answer(...)
    
    response, sources, chunks = answer(
        query=req.query,
        retrieval_config=retrieval_config
    )
    
    return {
        "chunks": chunks,
        "response": response
    }
