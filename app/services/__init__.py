# 服務模組初始化 
from app.services.quick_reply_manager import quick_reply_manager
from app.services.response_generator import response_generator
from app.services.sutra_retriever import sutra_retriever
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager

__all__ = [
    'quick_reply_manager',
    'response_generator',
    'sutra_retriever',
    'news_processor',
    'user_manager'
] 