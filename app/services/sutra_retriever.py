import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import settings
from app.services.vector_store import vector_store

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
        # 使用共享的向量存儲服務
        self.vector_store = vector_store
        
        # 檢查向量存儲服務是否可用
        self.cbeta_vectorstore_available = self.vector_store.embedding_available
        self.custom_vectorstore_available = self.vector_store.embedding_available
        
        if not self.cbeta_vectorstore_available:
            logger.warning("經文檢索器初始化失敗: 向量存儲服務不可用")
        else:
            logger.info("經文檢索器初始化成功")
    
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
            # 檢查向量存儲服務是否可用
            if not self.vector_store.embedding_available:
                logger.warning("經文查詢失敗: 向量存儲服務不可用")
                return self._get_fallback_results()
            
            # 準備過濾條件
            search_filter = None
            if filter_sutra:
                search_filter = {"source": filter_sutra}
            
            # 搜索CBETA經典
            cbeta_results = self.vector_store.search(
                query=user_query,
                collection_name="cbeta_sutras",
                filter_dict=search_filter,
                k=top_k
            )
            
            # 處理CBETA搜索結果
            for result in cbeta_results:
                result["custom_document"] = False
                results.append(result)
            
            logger.info(f"CBETA搜索結果數量: {len(cbeta_results)}")
            
            # 如果CBETA結果為空，使用後備結果
            if len(cbeta_results) == 0:
                logger.warning("CBETA搜索結果為空，使用後備結果")
                fallback_results = self._get_fallback_results()
                if fallback_results:
                    results.extend(fallback_results)
            
            # 搜索自定義文檔
            custom_results = self.vector_store.search(
                query=user_query,
                collection_name="custom_documents",
                k=top_k
            )
            
            # 處理自定義文檔搜索結果
            for result in custom_results:
                result["custom_document"] = True
                results.append(result)
            
            logger.info(f"自定義文檔搜索結果數量: {len(custom_results)}")
            
            # 按相關性排序結果
            results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
            
            # 限制結果數量
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"查詢經文時出錯: {e}", exc_info=True)
            return self._get_fallback_results()
    
    def _get_fallback_results(self) -> List[Dict]:
        """
        當向量搜索失敗時獲取後備結果
            
        Returns:
            List[Dict]: 後備結果
        """
        try:
            # 準備一些後備佛教教義，以防向量搜索失敗
            fallback_results = [
                {
                    "text": "佛陀教導我們，一切皆苦，苦由貪欲而生，斷除貪欲可得涅槃，而八正道是通往涅槃之路。這是佛教的四聖諦，是佛法的核心教義。",
                    "sutra": "《雜阿含經》",
                    "sutra_id": "T0099",
                    "relevance": 0.85,
                    "custom_document": False
                },
                {
                    "text": "菩薩修行六度波羅蜜：布施、持戒、忍辱、精進、禪定、般若。通過這六種修行，菩薩能夠累積福德和智慧，最終成就佛道。",
                    "sutra": "《大智度論》",
                    "sutra_id": "T1509",
                    "relevance": 0.82,
                    "custom_document": False
                },
                {
                    "text": "心若清淨，便見如來。所謂佛性，人人本具，只因妄想執著而不能證得。放下妄想，返歸本性，即是成佛之道。",
                    "sutra": "《六祖壇經》",
                    "sutra_id": "T2008",
                    "relevance": 0.80,
                    "custom_document": False
                }
            ]
            
            return fallback_results
            
        except Exception as e:
            logger.error(f"獲取後備結果時出錯: {e}", exc_info=True)
            return []

# 單例模式實例
sutra_retriever = SutraRetriever() 