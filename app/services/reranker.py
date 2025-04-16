"""
Reranker 模組 - 對檢索結果進行重排序

此模組實現了一個基於相似度計算的重排序系統，用於改善檢索結果的相關性。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings
from app.services import embedding_service

# 設置日誌
logger = logging.getLogger(__name__)

class Reranker:
    """
    檢索結果重排序器
    
    此類通過計算查詢與檢索結果的相似度來重新排序檢索結果，
    提高最相關內容在結果列表中的位置。
    """
    
    def __init__(self):
        """初始化重排序器"""
        # 使用已初始化的嵌入服務實例
        self.embedding_service = embedding_service
        logger.info("重排序器初始化完成")
        
    async def rerank(self, query: str, texts: List[str]) -> List[float]:
        """
        對檢索結果進行重排序
        
        Args:
            query: 用戶查詢
            texts: 待排序的文本列表
            
        Returns:
            List[float]: 每個文本的相關性分數
        """
        if not texts:
            return []
            
        try:
            # 計算查詢嵌入
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # 計算所有文本的嵌入
            text_embeddings = []
            for text in texts:
                # 使用非同步方式獲取嵌入
                text_embedding = await self.embedding_service.get_embedding(text)
                text_embeddings.append(text_embedding)
                
            # 計算查詢與每個文本的相似度
            scores = []
            for text_embedding in text_embeddings:
                # 使用餘弦相似度
                similarity = self._cosine_similarity(query_embedding, text_embedding)
                scores.append(similarity)
                
            logger.info(f"已完成 {len(texts)} 個文本的重排序")
            return scores
            
        except Exception as e:
            logger.error(f"重排序過程中發生錯誤: {str(e)}")
            # 如果發生錯誤，返回相等的分數
            return [1.0] * len(texts)
            
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        計算兩個向量的餘弦相似度
        
        Args:
            vec1: 第一個向量
            vec2: 第二個向量
            
        Returns:
            float: 餘弦相似度分數
        """
        # 轉換為numpy數組
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # 計算餘弦相似度
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        # 避免除以零
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
            
        similarity = dot_product / (norm_vec1 * norm_vec2)
        
        # 確保結果在 [0, 1] 範圍內
        return float(max(0.0, min(1.0, similarity)))
        
    @staticmethod
    async def rerank_with_custom_model(query: str, texts: List[str]) -> List[float]:
        """
        使用自定義模型進行重排序（擴展功能，將來實現）
        
        此方法為未來擴展預留。可以用來接入專門的重排序模型，
        如微軟的Cross-Encoder模型或其他專用於重排序的模型。
        
        Args:
            query: 用戶查詢
            texts: 待排序的文本列表
            
        Returns:
            List[float]: 每個文本的相關性分數
        """
        # 目前僅返回預設值，將來可以替換為實際實現
        logger.warning("自定義模型重排序功能尚未實現，返回預設分數")
        return [1.0] * len(texts)

# 創建單例實例
reranker = Reranker() 