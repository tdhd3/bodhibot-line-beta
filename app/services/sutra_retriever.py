import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
import uuid
import traceback

from app.core.config import settings
from app.services.vector_store import vector_store
from app.services import embedding_service

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
        
        # 使用共享的嵌入服務
        self.embedding_service = embedding_service
        
        # 檢查向量存儲服務是否可用
        self.cbeta_vectorstore_available = True  # 默認為可用
        self.custom_vectorstore_available = True  # 默認為可用
        
        # 導入重排序服務
        try:
            from app.services.reranker import reranker
            self.reranker = reranker
            self.rerank_available = True
            logger.info("經文檢索器成功集成重排序功能")
        except Exception as e:
            self.rerank_available = False
            logger.warning(f"無法導入重排序服務: {e}，將僅使用向量相似度排序")
        
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
        
        # 建立經典ID映射表，方便檢索 (包含全名和常用名)
        self.sutra_id_map = {
            "楞嚴經": "T0945", 
            "大佛頂首楞嚴經": "T0945",  # 全名
            "法華經": "T0262",
            "妙法蓮華經": "T0262",  # 全名
            "普賢行願品": "T0293",
            "地藏經": "T0412",
            "地藏菩薩本願經": "T0412",  # 全名
            "藥師經": "T0449",
            "藥師琉璃光如來本願功德經": "T0449",  # 全名
            "金剛經": "T0235",
            "金剛般若波羅蜜經": "T0235",  # 全名
            "六祖壇經": "T2008",
            "摩訶止觀": "T1911"
        }
        
        # 經典別名映射表（便於反向查找）
        self.sutra_aliases = {
            "T0945": ["楞嚴經", "大佛頂首楞嚴經"],
            "T0262": ["法華經", "妙法蓮華經"],
            "T0235": ["金剛經", "金剛般若波羅蜜經"],
            "T0412": ["地藏經", "地藏菩薩本願經"],
            "T0449": ["藥師經", "藥師琉璃光如來本願功德經"],
            "T0293": ["普賢行願品"],
            "T2008": ["六祖壇經"],
            "T1911": ["摩訶止觀"],
        }
        
        logger.info("經文檢索器初始化成功")
        logger.info(f"預設經典列表: {', '.join([s['name'] for s in self.default_sutras])}")
    
    async def query_sutra(self, user_query: str, filter_sutra: Optional[str] = None, top_k: int = 3, use_rerank: bool = True, use_hybrid: bool = True) -> List[Dict]:
        """
        查詢經文
        
        Args:
            user_query: 用戶查詢文本
            filter_sutra: 可選的經典名稱過濾器
            top_k: 返回的結果數量
            use_rerank: 是否使用重排序
            use_hybrid: 是否使用混合排序策略(考慮多樣性)
            
        Returns:
            List[Dict]: 相關經文片段清單，每個條目包含文本和元數據
        """
        results = []
        
        try:
            # 檢查向量存儲服務是否可用
            if not self.vector_store:
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
                try:
                    sutra_results = await self.vector_store.search(
                        query=user_query,
                        limit=top_k
                    )
                except TypeError as e:
                    # 處理參數不匹配的情況
                    logger.error(f"向量存儲search方法參數錯誤: {e}")
                    sutra_results = []
                except Exception as e:
                    logger.error(f"對經典 {sutra['name']} 進行搜索時出錯: {e}")
                    sutra_results = []
                
                # 處理搜索結果
                for result in sutra_results:
                    result["custom_document"] = False
                    default_results.append(result)
            
            # 如果預設經典中找到了足夠的結果，則使用這些結果
            if len(default_results) >= top_k:
                logger.info(f"預設經典搜索結果數量: {len(default_results)}")
                
                # 應用重排序（如果可用且啟用）
                if self.rerank_available and use_rerank:
                    if use_hybrid:
                        logger.info("使用混合重排序策略對預設經典搜索結果進行排序")
                        return self.reranker.hybrid_rerank(user_query, default_results, top_k)
                    else:
                        logger.info("使用交叉編碼器對預設經典搜索結果進行重排序")
                        return self.reranker.rerank(user_query, default_results, top_k)
                
                # 使用普通相似度排序
                default_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
                return default_results[:top_k]
            
            # 如果預設經典中結果不足，則搜索所有CBETA經典
            try:
                cbeta_results = await self.vector_store.search(
                    query=user_query,
                    limit=top_k
                )
            except TypeError as e:
                # 處理參數不匹配的情況
                logger.error(f"向量存儲search方法參數錯誤: {e}")
                cbeta_results = []
            except Exception as e:
                logger.error(f"搜索CBETA經典時出錯: {e}")
                cbeta_results = []
            
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
            try:
                custom_results = await self.vector_store.search(
                    query=user_query,
                    limit=top_k
                )
            except TypeError as e:
                # 處理參數不匹配的情況
                logger.error(f"向量存儲search方法參數錯誤: {e}")
                custom_results = []
            except Exception as e:
                logger.error(f"搜索自定義文檔時出錯: {e}")
                custom_results = []
            
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
            
            # 應用重排序（如果可用且啟用）
            if self.rerank_available and use_rerank:
                if use_hybrid:
                    logger.info("使用混合重排序策略對全部搜索結果進行排序")
                    return self.reranker.hybrid_rerank(user_query, unique_results, top_k)
                else:
                    logger.info("使用交叉編碼器對全部搜索結果進行重排序")
                    return self.reranker.rerank(user_query, unique_results, top_k)
            
            # 使用普通相似度排序
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

    async def search_by_query(
        self, 
        query: str, 
        limit: int = 5, 
        filter_obj: Optional[Dict[str, Any]] = None,
        use_rerank: bool = False,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        根據查詢字符串搜索相關經文

        Args:
            query: 查詢字符串
            limit: 返回結果數量限制
            filter_obj: 過濾條件
            use_rerank: 是否使用重排序功能
            use_hybrid: 是否使用混合搜索策略
            
        Returns:
            List[Dict]: 檢索到的經文列表
        """
        try:
            start_time = time.time()
            if not self.vector_store:
                logger.error("向量存儲服務不可用")
                return self._get_fallback_results()
                
            logger.info(f"搜索查詢: {query}")
            
            # 定義搜索策略
            search_results = []
            
            if use_hybrid:
                # 混合搜索策略 (向量 + 關鍵詞搜索)
                try:
                    # 向量搜索部分
                    vector_results = await self._vector_search(query, limit=limit, filter_obj=filter_obj)
                    
                    # 關鍵詞搜索部分
                    keyword_results = await self._keyword_search(query, limit=limit, filter_obj=filter_obj)
                    
                    # 合併結果（去重）
                    combined_results = vector_results.copy()
                    seen_ids = {doc["id"] for doc in combined_results}
                    
                    for doc in keyword_results:
                        if doc["id"] not in seen_ids:
                            combined_results.append(doc)
                            seen_ids.add(doc["id"])
                    
                    search_results = combined_results[:limit]
                    
                except Exception as e:
                    logger.error(f"混合搜索失敗: {str(e)}", exc_info=True)
                    # 回退到單一向量搜索
                    search_results = await self._vector_search(query, limit=limit, filter_obj=filter_obj)
            else:
                # 僅使用向量搜索
                search_results = await self._vector_search(query, limit=limit, filter_obj=filter_obj)
            
            # 檢查搜索結果是否為空
            if not search_results:
                logger.warning("向量搜索未返回結果，使用後備結果")
                return self._get_fallback_results()
            
            # 應用重排序功能（如果啟用）
            reranked_results = []
            if use_rerank and search_results:
                try:
                    from app.services.reranker import Reranker
                    reranker = Reranker()
                    
                    # 對檢索到的結果進行重排序
                    texts = [doc.get("text", "") for doc in search_results]
                    scores = await reranker.rerank(query, texts)
                    
                    # 根據重排序的分數對結果進行排序
                    for i, score in enumerate(scores):
                        search_results[i]["rerank_score"] = float(score)
                    
                    reranked_results = sorted(search_results, key=lambda x: x.get("rerank_score", 0), reverse=True)
                    logger.info(f"重排序完成，共處理 {len(reranked_results)} 個結果")
                except Exception as e:
                    logger.error(f"重排序失敗: {str(e)}", exc_info=True)
                    # 如果重排序失敗，將繼續使用原始排序的結果
                    reranked_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)
            else:
                # 不使用重排序時，按原始相似度排序
                reranked_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)
            
            results = []
            
            # 處理搜索結果
            for item in reranked_results[:limit]:
                page_content = item.get("text", "")
                metadata = item.get("metadata", {})
                
                if not page_content:
                    continue
                
                # 構建結果字典
                result = {
                    "text": page_content,
                    "sutra": metadata.get("sutra", ""),
                    "sutra_id": metadata.get("sutra_id", ""),
                    "similarity": item.get("score", 0),
                    "rerank_score": item.get("rerank_score", None),
                    "volume": metadata.get("volume", ""),
                    "juan": metadata.get("juan", ""),
                    "page": metadata.get("page", ""),
                    "source": f"{metadata.get('sutra', '')} ({metadata.get('volume', '')}.{metadata.get('juan', '')}.{metadata.get('page', '')})"
                }
                
                # 簡化經名顯示（如果在別名字典中）
                for full_name, short_name in self.sutra_aliases.items():
                    if full_name in result["sutra"]:
                        result["display_name"] = short_name
                        break
                
                results.append(result)

            # 如果處理後結果為空，返回後備結果
            if not results:
                logger.warning("處理後搜索結果為空，使用後備結果")
                return self._get_fallback_results()
                
            end_time = time.time()
            logger.info(f"搜索完成，耗時 {end_time - start_time:.2f} 秒，找到 {len(results)} 個結果")
            
            return results
            
        except Exception as e:
            logger.error(f"搜索失敗: {str(e)}", exc_info=True)
            logger.error(traceback.format_exc())
            # 返回後備結果
            return self._get_fallback_results()
            
    async def _vector_search(self, query: str, limit: int = 5, filter_obj: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """執行向量搜索"""
        try:
            # 檢查嵌入服務是否可用
            if not self.embedding_service.embedding_available:
                logger.warning("嵌入服務不可用，使用後備結果替代向量搜索")
                return []
                
            # 獲取查詢嵌入
            embedding = await self.embedding_service.get_embedding(query)
            
            # 確保embedding不為None
            if not embedding:
                logger.warning("生成查詢嵌入失敗，返回空結果")
                return []
            
            try:
                # 執行向量搜索
                results = self.vector_store.similarity_search_with_score_by_vector(
                    embedding, 
                    k=limit,
                    filter=filter_obj
                )
            except AttributeError as e:
                # 處理vector_store沒有similarity_search_with_score_by_vector方法的情況
                logger.error(f"向量存儲不支持向量搜索: {e}")
                # 嘗試使用普通搜索
                try:
                    results = await self.vector_store.search(query, limit=limit)
                    formatted_results = []
                    for doc in results:
                        formatted_results.append({
                            "id": doc.get("id", str(uuid.uuid4())),
                            "text": doc.get("content", ""),
                            "metadata": doc.get("metadata", {}),
                            "score": 1.0 - (doc.get("distance", 0) or 0)
                        })
                    return formatted_results
                except Exception as e2:
                    logger.error(f"嘗試替代搜索方法也失敗: {e2}")
                    return []
            
            # 格式化結果
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "id": doc.metadata.get("id", str(uuid.uuid4())),
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
                
            return formatted_results
        except Exception as e:
            logger.error(f"向量搜索失敗: {str(e)}", exc_info=True)
            return []
            
    async def _keyword_search(self, query: str, limit: int = 5, filter_obj: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """執行關鍵詞搜索"""
        try:
            # 從查詢中提取關鍵詞
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(query, topK=5)
            
            if not keywords:
                return []
                
            # 構建查詢條件
            keyword_query = " OR ".join(keywords)
            
            # 通過 Chroma 執行關鍵詞搜索
            results = self.vector_store._collection.search(
                query_texts=[keyword_query],
                n_results=limit,
                where=filter_obj
            )
            
            # 格式化結果
            formatted_results = []
            if results and results.get('documents') and results.get('metadatas'):
                for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                    # 提取文檔ID和相似度分數
                    doc_id = metadata.get("id", str(uuid.uuid4()))
                    
                    # 使用距離的倒數作為分數（簡單近似）
                    score = results.get('distances', [[]])[0][i] if results.get('distances') else 0.5
                    if score > 0:  # 避免除以零
                        score = 1.0 / score
                    
                    formatted_results.append({
                        "id": doc_id,
                        "text": doc,
                        "metadata": metadata,
                        "score": float(score)
                    })
                
            return formatted_results
        except Exception as e:
            logger.error(f"關鍵詞搜索失敗: {str(e)}")
            return []

# 單例模式實例
sutra_retriever = SutraRetriever() 