import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema.document import Document

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SutraRetriever:
    """
    經文檢索器類別
    負責從向量資料庫中檢索與用戶問題相關的經文片段
    """
    
    def __init__(self):
        """初始化經文檢索器"""
        self.vector_db_path = Path(settings.VECTOR_DB_PATH)
        
        # 檢查向量資料庫路徑是否存在
        if not self.vector_db_path.exists():
            logger.warning(f"向量資料庫路徑不存在: {self.vector_db_path}")
            self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL
        )
        
        # 初始化CBETA經典向量資料庫
        self.cbeta_vectorstore = self._init_vectorstore("cbeta_sutras")
        
        # 初始化自定義文檔向量資料庫
        self.custom_vectorstore = self._init_vectorstore("custom_documents")
    
    def _init_vectorstore(self, collection_name: str):
        """
        初始化向量資料庫
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            向量資料庫對象或None
        """
        try:
            return Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.vector_db_path)
            )
        except Exception as e:
            logger.error(f"初始化向量資料庫失敗 {collection_name}: {e}", exc_info=True)
            return None
    
    async def query_sutra(self, user_query: str, filter_sutra: Optional[str] = None, top_k: int = 3) -> List[Dict]:
        """
        查詢經文
        
        Args:
            user_query: 用戶查詢文本
            filter_sutra: 可選的經典名稱過濾器
            top_k: 返回的結果數量
            
        Returns:
            List[Dict]: 相關經文片段清單，每個條目包含文本和元數據
        """
        results = []
        
        try:
            # 檢查CBETA向量資料庫是否可用
            if self.cbeta_vectorstore:
                # 準備過濾條件
                search_filter = None
                if filter_sutra:
                    search_filter = {"source": filter_sutra}
                
                # 搜索CBETA經典
                cbeta_docs = self.cbeta_vectorstore.similarity_search_with_score(
                    user_query,
                    k=top_k,
                    filter=search_filter
                )
                
                # 處理CBETA搜索結果
                for doc, score in cbeta_docs:
                    results.append({
                        "text": doc.page_content,
                        "sutra": doc.metadata.get("source", "未知經典"),
                        "sutra_id": doc.metadata.get("sutra_id", ""),
                        "title": doc.metadata.get("title", ""),
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                        "relevance": float(1.0 - score)  # 將距離轉換為相關性分數
                    })
                
                logger.info(f"CBETA搜索結果數量: {len(cbeta_docs)}")
                
            # 檢查自定義文檔向量資料庫是否可用
            if self.custom_vectorstore:
                # 搜索自定義文檔
                custom_docs = self.custom_vectorstore.similarity_search_with_score(
                    user_query,
                    k=top_k
                )
                
                # 處理自定義文檔搜索結果
                for doc, score in custom_docs:
                    results.append({
                        "text": doc.page_content,
                        "source": doc.metadata.get("source", "自定義文檔"),
                        "file_type": doc.metadata.get("file_type", ""),
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                        "custom_document": True,
                        "relevance": float(1.0 - score)
                    })
                
                logger.info(f"自定義文檔搜索結果數量: {len(custom_docs)}")
            
            # 按相關性排序結果
            results.sort(key=lambda x: x["relevance"], reverse=True)
            
            # 限制結果數量
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"查詢經文時出錯: {e}", exc_info=True)
            return []
    
    async def get_context_window(self, sutra: str, sutra_id: str, chunk_id: int, window_size: int = 1) -> Dict:
        """
        獲取經文片段的上下文窗口
        
        Args:
            sutra: 經典名稱
            sutra_id: 經典ID
            chunk_id: 片段ID
            window_size: 上下文窗口大小（每側的片段數）
            
        Returns:
            Dict: 上下文窗口，包含前後的文本片段
        """
        if not self.cbeta_vectorstore:
            return {"before": [], "after": []}
        
        context = {"before": [], "after": []}
        
        try:
            # 獲取前面的片段
            for i in range(1, window_size + 1):
                prev_chunk_id = chunk_id - i
                if prev_chunk_id < 0:
                    continue
                
                filter_dict = {
                    "sutra_id": sutra_id,
                    "chunk_id": prev_chunk_id
                }
                
                prev_docs = self.cbeta_vectorstore.get(
                    where=filter_dict,
                    limit=1
                )
                
                if prev_docs and prev_docs["documents"]:
                    context["before"].insert(0, {
                        "text": prev_docs["documents"][0],
                        "chunk_id": prev_chunk_id
                    })
            
            # 獲取後面的片段
            for i in range(1, window_size + 1):
                next_chunk_id = chunk_id + i
                
                filter_dict = {
                    "sutra_id": sutra_id,
                    "chunk_id": next_chunk_id
                }
                
                next_docs = self.cbeta_vectorstore.get(
                    where=filter_dict,
                    limit=1
                )
                
                if next_docs and next_docs["documents"]:
                    context["after"].append({
                        "text": next_docs["documents"][0],
                        "chunk_id": next_chunk_id
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"獲取上下文窗口時出錯: {e}", exc_info=True)
            return {"before": [], "after": []}

# 單例模式實例
sutra_retriever = SutraRetriever() 