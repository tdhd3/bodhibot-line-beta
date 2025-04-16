# 服務模塊
# 確保正確的導入順序，避免循環導入

# 先導入基礎服務
from app.services.vector_store import vector_store
from app.services.scripture_search import scripture_search
from app.services.conversation_store import conversation_store

# 然後導入依賴這些基礎服務的其他服務
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager

__all__ = [
    'quick_reply_manager',
    'response_generator',
    'vector_store',
    'scripture_search',
    'conversation_store',
    'news_processor',
    'user_manager'
] 