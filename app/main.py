import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes.line_webhook import router as line_router
from app.data_processing.file_processor import FileProcessor
from app.data_processing.cbeta_processor import CBETAProcessor

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 創建FastAPI應用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有方法
    allow_headers=["*"],  # 允許所有標頭
)

# 創建API路由
api_router = APIRouter(prefix=settings.API_PREFIX)

# 包含LINE Bot路由
api_router.include_router(line_router, prefix="/line", tags=["LINE Bot"])

# 包含API路由
app.include_router(api_router)

# 文件處理器
file_processor = None

# CBETA處理器
cbeta_processor = None

@app.on_event("startup")
async def startup_event():
    """應用程式啟動時執行"""
    global file_processor, cbeta_processor
    
    try:
        # 初始化檔案處理器
        file_processor = FileProcessor()
        
        # 初始化CBETA處理器
        cbeta_processor = CBETAProcessor()
        
        # 在背景任務中啟動檔案監視
        asyncio.create_task(file_processor.watch_folder())
        
        logger.info("應用程式成功啟動")
        
    except Exception as e:
        logger.error(f"應用程式啟動時出錯: {e}", exc_info=True)

@app.get("/")
async def root():
    """根路徑處理器"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康檢查接口"""
    return {"status": "healthy"}

@app.get("/process-cbeta")
async def process_cbeta():
    """手動觸發CBETA經典處理"""
    global cbeta_processor
    
    if not cbeta_processor:
        cbeta_processor = CBETAProcessor()
    
    # 在背景任務中處理
    asyncio.create_task(cbeta_processor.process_all_sutras())
    
    return {"status": "processing", "message": "已開始處理CBETA經典，此過程可能需要一些時間。"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局異常處理器"""
    logger.error(f"全局異常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "內部伺服器錯誤", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    
    # 本地運行
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 