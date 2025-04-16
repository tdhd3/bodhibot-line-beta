"""
嵌入服務
管理文本的向量嵌入表示
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings
from langchain_openai import OpenAIEmbeddings

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    嵌入服務
    負責生成文本的向量嵌入表示
    """
    
    def __init__(self):
        """初始化嵌入服務"""
        try:
            # 檢查API密鑰是否可用
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model=settings.EMBEDDING_MODEL
                )
                self.embedding_available = True
                logger.info("嵌入服務初始化成功，使用模型: " + settings.EMBEDDING_MODEL)
            else:
                logger.warning("未設置OpenAI API密鑰，將使用假嵌入")
                self.embeddings = None
                self.embedding_available = False
        except Exception as e:
            logger.error(f"初始化嵌入服務時出錯: {e}")
            self.embeddings = None
            self.embedding_available = False
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        獲取文本的嵌入向量表示
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            List[float]: 嵌入向量
        """
        try:
            if not self.embedding_available or not self.embeddings:
                logger.warning("嵌入服務不可用，返回假嵌入")
                # 返回固定維度的隨機向量作為假嵌入
                return self._get_fake_embedding()
            
            # 使用OpenAI嵌入模型生成嵌入
            embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                text
            )
            
            return embedding
        except Exception as e:
            logger.error(f"生成嵌入時出錯: {e}")
            return self._get_fake_embedding()
    
    def _get_fake_embedding(self, dim: int = 1536) -> List[float]:
        """
        生成假嵌入向量
        當真實嵌入服務不可用時使用
        
        Args:
            dim: 嵌入向量的維度
            
        Returns:
            List[float]: 固定的假嵌入向量
        """
        # 使用固定的種子生成相同的隨機向量，確保相同文本產生相同的假嵌入
        np.random.seed(hash(str("fixed_seed")) % 2**32)
        
        # 生成隨機向量並歸一化
        fake_embedding = np.random.normal(0, 1, dim)
        fake_embedding = fake_embedding / np.linalg.norm(fake_embedding)
        
        return fake_embedding.tolist() 