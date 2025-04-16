# 服務模塊
# 確保正確的導入順序，避免循環導入

# 首先導入基礎設定
from app.core.config import settings

# 先創建嵌入服務實例
from app.services.embedding_service import EmbeddingService
embedding_service = EmbeddingService()

# 然後導入向量存儲和其他基礎服務
from app.services.vector_store import vector_store
from app.services.scripture_search import scripture_search
from app.services.conversation_store import conversation_store

# 最後導入依賴這些基礎服務的其他服務
from app.services.reranker import reranker
from app.services.sutra_retriever import sutra_retriever
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager
from app.services.sutra_recommender import sutra_recommender

__all__ = [
    'embedding_service',
    'vector_store',
    'reranker',
    'sutra_retriever',
    'quick_reply_manager',
    'response_generator',
    'scripture_search',
    'conversation_store',
    'news_processor',
    'user_manager',
    'sutra_recommender'
] 