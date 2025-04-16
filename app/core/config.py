import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 載入.env檔案中的環境變數
load_dotenv()

class Settings:
    # 基本設定
    PROJECT_NAME: str = "菩薩小老師"
    PROJECT_VERSION: str = "0.1.0"
    DESCRIPTION: str = "以慈悲智慧引導的佛法修學與生活應用LINE對話系統"
    
    # API設定
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 資料庫設定
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bodhibot.db")
    
    # LINE Bot設定
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    WEBHOOK_PATH: str = "/webhook"
    
    # OpenAI設定
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4o-mini")  # 默認使用 gpt-4o-mini
    
    # 向量資料庫設定
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "data/chroma_db")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "sutras")
    
    # 資料路徑設定
    INPUT_FOLDER: str = os.getenv("INPUT_FOLDER", "./data/input")
    OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", "./data/output")
    CBETA_FOLDER: str = os.getenv("CBETA_FOLDER", "./data/cbeta")
    
    # CBETA資料設定
    CBETA_URL_BASE: str = "https://cbetaonline.dila.edu.tw"
    SUPPORTED_SUTRAS: list = [
        {"name": "楞嚴經", "id": "T0945"},
        {"name": "法華經", "id": "T0262"},
        {"name": "普賢行願品", "id": "T0293"},
        {"name": "地藏經", "id": "T0412"},
        {"name": "藥師經", "id": "T0449"},
        {"name": "金剛經", "id": "T0235"},
        {"name": "六祖壇經", "id": "T2008"}, 
        {"name": "摩訶止觀", "id": "T1911"},
    ]
    
    # Redis設定 (用於使用者狀態管理)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() == "true"
    
    # 分塊設定
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    
    # 新聞設定
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")
    NEWS_UPDATE_INTERVAL: int = int(os.getenv("NEWS_UPDATE_INTERVAL", "3600"))  # 默認1小時更新一次
    
    # 快速回覆設定
    MAX_QUICK_REPLIES: int = int(os.getenv("MAX_QUICK_REPLIES", "13"))
    SUGGESTION_LIMIT: int = int(os.getenv("SUGGESTION_LIMIT", "3"))
    HISTORY_LIMIT: int = int(os.getenv("HISTORY_LIMIT", "5"))
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "50"))
    
    # 用戶回饋表單
    USER_FEEDBACK_FORM: str = os.getenv("USER_FEEDBACK_FORM", "https://docs.google.com/forms/d/17B148aK3REfbUEtmi3isQQEkQwvvIlaKgte00Yde_zE/edit")
    
    # 視覺化設定
    ENABLE_MARKDOWN: bool = True
    ENABLE_EMOJI: bool = True
    THEME_COLOR: str = "#1DB446"  # 主題顏色，用於Flex Message頭部
    MAX_IMAGE_WIDTH: int = 1024    # 圖片最大寬度
    MAX_IMAGE_HEIGHT: int = 1024   # 圖片最大高度
    FONT_SIZE_LARGE: str = "lg"    # 大字體尺寸
    FONT_SIZE_MEDIUM: str = "md"   # 中字體尺寸
    FONT_SIZE_SMALL: str = "sm"    # 小字體尺寸

# 實例化設定
settings = Settings()

# 以下全局變數不再需要，已合併到Settings類中
# MAX_HISTORY_MESSAGES = 50
# CHROMA_DB_DIR = "data/chroma_db"
# CHROMA_COLLECTION_NAME = "sutras" 