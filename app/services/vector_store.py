"""
向量存儲服務
管理文本的向量表示與檢索
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
from chromadb.config import Settings

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorStore:
    """
    向量存儲服務
    負責經文和用戶問題的向量化和檢索
    """
    
    def __init__(self):
        """初始化向量存儲服務"""
        self.chroma_client = None
        self.collection = None
        
        try:
            # 創建向量存儲目錄
            os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
            
            # 初始化Chroma客戶端
            self.chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_DIR,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
            
            # 獲取或創建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("向量存儲初始化成功")
        except Exception as e:
            logger.error(f"初始化向量存儲時出錯: {e}", exc_info=True)
            raise
    
    async def search(self, query, limit=5):
        """
        搜索相關文檔
        
        Args:
            query: 查詢字符串
            limit: 返回結果數量
            
        Returns:
            List: 相關文檔列表
        """
        try:
            if not self.collection:
                logger.error("向量集合未初始化")
                return []
            
            # 執行相似度搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            # 處理結果
            documents = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    documents.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 1.0
                    })
            
            return documents
        except Exception as e:
            logger.error(f"搜索向量存儲時出錯: {e}", exc_info=True)
            return []

# 單例模式實例
vector_store = VectorStore() 