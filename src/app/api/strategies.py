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
    sparse_top_k: int = 10
    hybrid_top_k: int = 10
    vector_store_query_mode: str = "hybrid"
    alpha: float = 0.5
    rerank_top_k: int = 5
    description: Optional[str] = None

class StrategyResponse(BaseModel):
    id: str
    name: str
    initial_top_k: int
    sparse_top_k: int
    hybrid_top_k: int
    vector_store_query_mode: str
    alpha: float
    rerank_top_k: int
    description: Optional[str]

    class Config:
        from_attributes = True

class TestStrategyRequest(BaseModel):
    query: str
    file_names: Optional[List[str]] = None
    initial_top_k: int = 10
    sparse_top_k: int = 10
    hybrid_top_k: int = 10
    vector_store_query_mode: str = "hybrid"
    alpha: float = 0.5
    rerank_top_k: int = 5

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
        strategy.sparse_top_k, 
        strategy.hybrid_top_k, 
        strategy.vector_store_query_mode, 
        strategy.alpha, 
        strategy.rerank_top_k, 
        None,  # score_threshold
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
        "sparse_top_k": req.sparse_top_k,
        "hybrid_top_k": req.hybrid_top_k,
        "vector_store_query_mode": req.vector_store_query_mode,
        "alpha": req.alpha,
        "rerank_top_k": req.rerank_top_k
    }
    
    # Call answer with config and file_names
    response, sources, chunks = answer(
        query=req.query,
        file_names=req.file_names,
        retrieval_config=retrieval_config
    )
    
    return {
        "answer": response,
        "chunks": chunks
    }
