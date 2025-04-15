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

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorStore:
    """
    向量存儲服務
    處理文本的向量表示與檢索
    """
    
    def __init__(self):
        """初始化向量存儲"""
        self.vector_db_path = Path(settings.VECTOR_DB_PATH)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 準備嵌入模型
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model=settings.EMBEDDING_MODEL
                )
                self.embedding_available = True
                logger.info("向量存儲服務初始化成功")
            except Exception as e:
                logger.error(f"初始化OpenAI嵌入模型失敗: {e}", exc_info=True)
                self.embedding_available = False
                self.embeddings = None
        else:
            logger.warning("未設置OpenAI API Key，向量存儲功能將不可用")
            self.embeddings = None
            self.embedding_available = False
        
        # 準備文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )
        
        # 初始化向量存儲
        if self.embedding_available:
            try:
                self.vectorstore = Chroma(
                    collection_name="documents",
                    embedding_function=self.embeddings,
                    persist_directory=str(self.vector_db_path)
                )
                logger.info("向量存儲初始化成功")
            except Exception as e:
                logger.error(f"初始化向量存儲時出錯: {e}")
                self.vectorstore = None
        else:
            self.vectorstore = None
    
    def get_vectorstore(self, collection_name: str):
        """
        獲取向量存儲對象
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            向量存儲對象或None
        """
        if not self.embedding_available:
            logger.warning(f"嵌入模型不可用，無法獲取向量存儲: {collection_name}")
            return None
        
        try:
            return Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.vector_db_path)
            )
        except Exception as e:
            logger.error(f"獲取向量存儲失敗 {collection_name}: {e}", exc_info=True)
            return None
    
    def add_texts(self, texts: List[str], metadatas: List[Dict], collection_name: str) -> bool:
        """
        添加文本到向量存儲
        
        Args:
            texts: 文本列表
            metadatas: 元數據列表
            collection_name: 集合名稱
            
        Returns:
            bool: 成功返回True，否則返回False
        """
        if not self.embedding_available:
            logger.warning("嵌入模型不可用，無法添加文本到向量存儲")
            return False
        
        try:
            vectorstore = self.get_vectorstore(collection_name)
            if not vectorstore:
                return False
            
            vectorstore.add_texts(texts, metadatas)
            vectorstore.persist()
            logger.info(f"成功添加 {len(texts)} 個文本到向量存儲 {collection_name}")
            return True
        except Exception as e:
            logger.error(f"添加文本到向量存儲時出錯: {e}", exc_info=True)
            return False
    
    def search(self, query: str, collection_name: str, filter_dict: Optional[Dict] = None, k: int = 3) -> List[Dict]:
        """
        搜索向量存儲
        
        Args:
            query: 查詢文本
            collection_name: 集合名稱
            filter_dict: 過濾條件
            k: 返回結果數量
            
        Returns:
            List[Dict]: 搜索結果列表
        """
        if not self.embedding_available:
            logger.warning("嵌入模型不可用，無法執行搜索")
            return []
        
        try:
            vectorstore = self.get_vectorstore(collection_name)
            if not vectorstore:
                return []
            
            results = vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
            
            formatted_results = []
            for doc, score in results:
                result = {
                    "text": doc.page_content,
                    "relevance": float(1.0 - score)  # 將距離轉換為相關性分數
                }
                # 添加元數據
                for key, value in doc.metadata.items():
                    result[key] = value
                
                formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            logger.error(f"搜索向量存儲時出錯: {e}", exc_info=True)
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        獲取向量存儲的統計信息
        
        Returns:
            Dict: 包含統計信息的字典
        """
        if not self.embedding_available or not self.vectorstore:
            logger.warning("向量存儲不可用，無法獲取統計信息")
            return {"status": "unavailable"}
        
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                "status": "available",
                "count": count,
                "collection_name": "documents",
                "path": str(self.vector_db_path)
            }
            
        except Exception as e:
            logger.error(f"獲取向量存儲統計信息時出錯: {e}")
            return {"status": "error", "message": str(e)} 

# 單例模式實例
vector_store = VectorStore() 