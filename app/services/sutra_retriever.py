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
        
        # 定義預設經典列表
        self.default_sutras = [
            {"name": "楞嚴經", "id": "T0945"},
            {"name": "法華經", "id": "T0262"},
            {"name": "普賢行願品", "id": "T0293"},
            {"name": "地藏經", "id": "T0412"},
            {"name": "藥師經", "id": "T0449"},
            {"name": "金剛經", "id": "T0235"},
            {"name": "六祖壇經", "id": "T2008"},
            {"name": "摩訶止觀", "id": "T1911"}  # 包含六妙門的內容
        ]
        
        # 建立經典ID映射表，方便檢索
        self.sutra_id_map = {sutra["name"]: sutra["id"] for sutra in self.default_sutras}
        
        if not self.cbeta_vectorstore_available:
            logger.warning("經文檢索器初始化失敗: 向量存儲服務不可用")
        else:
            logger.info("經文檢索器初始化成功")
            logger.info(f"預設經典列表: {', '.join([s['name'] for s in self.default_sutras])}")
    
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
                # 如果提供了特定經典名稱，則僅搜索該經典
                if filter_sutra in self.sutra_id_map:
                    # 如果是預設經典之一，使用其ID作為過濾條件
                    search_filter = {"sutra_id": self.sutra_id_map[filter_sutra]}
                else:
                    # 否則使用經典名稱作為過濾條件
                    search_filter = {"source": filter_sutra}
            
            # 首先在預設經典中搜索
            default_results = []
            for sutra in self.default_sutras:
                # 對每部預設經典進行搜索
                sutra_filter = {"sutra_id": sutra["id"]}
                sutra_results = self.vector_store.search(
                    query=user_query,
                    collection_name="cbeta_sutras",
                    filter_dict=sutra_filter,
                    k=top_k
                )
                
                # 處理搜索結果
                for result in sutra_results:
                    result["custom_document"] = False
                    default_results.append(result)
            
            # 如果預設經典中找到了足夠的結果，則使用這些結果
            if len(default_results) >= top_k:
                logger.info(f"預設經典搜索結果數量: {len(default_results)}")
                # 按相關性排序結果
                default_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
                return default_results[:top_k]
            
            # 如果預設經典中結果不足，則搜索所有CBETA經典
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
            
            # 合併預設經典搜索結果和CBETA搜索結果
            all_results = default_results + results
            
            # 如果結果為空，使用後備結果
            if len(all_results) == 0:
                logger.warning("搜索結果為空，使用後備結果")
                fallback_results = self._get_fallback_results()
                if fallback_results:
                    all_results.extend(fallback_results)
            
            # 搜索自定義文檔
            custom_results = self.vector_store.search(
                query=user_query,
                collection_name="custom_documents",
                k=top_k
            )
            
            # 處理自定義文檔搜索結果
            for result in custom_results:
                result["custom_document"] = True
                all_results.append(result)
            
            logger.info(f"自定義文檔搜索結果數量: {len(custom_results)}")
            
            # 移除重複結果（基於sutra_id和text）
            unique_results = []
            seen_ids = set()
            for result in all_results:
                result_id = result.get("sutra_id", "") + result.get("text", "")[:50]
                if result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
            
            # 按相關性排序結果
            unique_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
            
            # 限制結果數量
            return unique_results[:top_k]
            
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
            # 使用預設經典作為後備結果
            fallback_results = [
                {
                    "text": "楞嚴經雲：「一切業障，皆從妄想生。若欲懺悔，端坐念實相。」修行者當觀照自心，認識真實本性。",
                    "sutra": "《楞嚴經》",
                    "sutra_id": "T0945",
                    "relevance": 0.85,
                    "custom_document": False
                },
                {
                    "text": "法華經說：「諸佛兩足尊，知法常無性，佛種從緣起，是故說一乘。」一切眾生皆有佛性，終將成佛。",
                    "sutra": "《法華經》",
                    "sutra_id": "T0262",
                    "relevance": 0.82,
                    "custom_document": False
                },
                {
                    "text": "金剛經云：「凡所有相，皆是虛妄。若見諸相非相，即見如來。」應離一切相而修行，不執著於任何形式。",
                    "sutra": "《金剛經》",
                    "sutra_id": "T0235",
                    "relevance": 0.80,
                    "custom_document": False
                },
                {
                    "text": "六祖惠能云：「菩提本無樹，明鏡亦非台，本來無一物，何處惹塵埃？」心若清淨，便見如來。",
                    "sutra": "《六祖壇經》",
                    "sutra_id": "T2008",
                    "relevance": 0.78,
                    "custom_document": False
                }
            ]
            
            return fallback_results
            
        except Exception as e:
            logger.error(f"獲取後備結果時出錯: {e}", exc_info=True)
            return []

# 單例模式實例
sutra_retriever = SutraRetriever() 