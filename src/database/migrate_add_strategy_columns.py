"""
Migration script to add missing columns to retrieval_strategy table
"""
from sqlalchemy import text
from src.database.connect_db import engine

def migrate():
    """Add missing columns to retrieval_strategy table"""
    
    # Get list of columns that might be missing
    columns_to_add = [
        ("sparse_top_k", "INTEGER DEFAULT 10"),
        ("hybrid_top_k", "INTEGER DEFAULT 10"),
        ("vector_store_query_mode", "VARCHAR DEFAULT 'hybrid'"),
        ("alpha", "REAL DEFAULT 0.5"),
        ("rerank_top_k", "INTEGER DEFAULT 5"),
        ("score_threshold", "REAL"),
        ("description", "VARCHAR"),
    ]
    
    with engine.connect() as conn:
        # Check which columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'retrieval_strategy'
        """))
        existing_columns = {row[0] for row in result}
        
        print(f"Existing columns: {existing_columns}")
        
        # Add missing columns
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"Adding column: {col_name}")
                conn.execute(text(f"""
                    ALTER TABLE retrieval_strategy 
                    ADD COLUMN {col_name} {col_type}
                """))
                conn.commit()
                print(f"✅ Added column: {col_name}")
            else:
                print(f"⏭️  Column already exists: {col_name}")
        
        print("\n✅ Migration completed!")

if __name__ == "__main__":
    migrate()
