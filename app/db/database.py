from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 創建SQLAlchemy引擎
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 定義Base類，用於創建資料庫模型
Base = declarative_base()

def get_db():
    """
    獲取資料庫會話
    
    Yields:
        Session: 資料庫會話
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 