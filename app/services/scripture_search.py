import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.services.vector_store import vector_store

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScriptureSearch:
    """
    經文檢索服務
    負責檢索相關經文和文檔
    """
    
    def __init__(self):
        """初始化經文檢索服務"""
        self.vector_store = vector_store
        logger.info("經文檢索服務初始化成功")
    
    async def search_by_query(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        根據查詢字符串搜索相關經文
        
        Args:
            query: 查詢字符串
            limit: 返回結果數量
            
        Returns:
            List[Dict]: 相關經文列表
        """
        try:
            # 使用向量存儲搜索相關文檔
            results = await self.vector_store.search(query, limit=limit)
            
            # 格式化結果
            scriptures = []
            for doc in results:
                scripture = {
                    "text": doc.get("content", ""),
                    "sutra": doc.get("metadata", {}).get("source", "佛教經典"),
                    "sutra_id": doc.get("metadata", {}).get("id", ""),
                    "relevance": 1.0 - (doc.get("distance", 0) or 0)
                }
                scriptures.append(scripture)
            
            return scriptures
        except Exception as e:
            logger.error(f"搜索經文時出錯: {e}", exc_info=True)
            return []
    
    async def get_sutra_by_id(self, sutra_id: str) -> Optional[Dict[str, Any]]:
        """
        根據經文ID獲取經文詳情
        
        Args:
            sutra_id: 經文ID
            
        Returns:
            Optional[Dict]: 經文詳情
        """
        try:
            # 這裡應該實現根據ID檢索的邏輯
            # 簡單起見，目前返回一個空結果
            return None
        except Exception as e:
            logger.error(f"獲取經文詳情時出錯: {e}", exc_info=True)
            return None

# 單例模式實例
scripture_search = ScriptureSearch() 