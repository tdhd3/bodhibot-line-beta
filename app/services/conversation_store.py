import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationStore:
    """
    對話存儲服務
    負責存儲和檢索用戶對話歷史
    """
    
    def __init__(self):
        """初始化對話存儲服務"""
        # 內存存儲，實際應用中應使用資料庫
        self.conversations = {}
        logger.info("對話存儲服務初始化成功")
    
    async def store_message(self, user_id: str, role: str, content: str) -> bool:
        """
        存儲消息
        
        Args:
            user_id: 用戶ID
            role: 消息角色 (user/assistant)
            content: 消息內容
            
        Returns:
            bool: 成功返回True，否則返回False
        """
        try:
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 追加消息
            self.conversations[user_id].append(message)
            
            # 限制歷史記錄長度
            max_history = settings.MAX_HISTORY_MESSAGES
            if len(self.conversations[user_id]) > max_history:
                self.conversations[user_id] = self.conversations[user_id][-max_history:]
            
            return True
        except Exception as e:
            logger.error(f"存儲消息時出錯: {e}", exc_info=True)
            return False
    
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        獲取對話歷史
        
        Args:
            user_id: 用戶ID
            limit: 最大消息數量
            
        Returns:
            List[Dict]: 對話歷史列表
        """
        try:
            if user_id not in self.conversations:
                return []
            
            # 返回最近的消息
            return self.conversations[user_id][-limit:]
        except Exception as e:
            logger.error(f"獲取對話歷史時出錯: {e}", exc_info=True)
            return []
    
    async def clear_conversation_history(self, user_id: str) -> bool:
        """
        清除對話歷史
        
        Args:
            user_id: 用戶ID
            
        Returns:
            bool: 成功返回True，否則返回False
        """
        try:
            if user_id in self.conversations:
                self.conversations[user_id] = []
            return True
        except Exception as e:
            logger.error(f"清除對話歷史時出錯: {e}", exc_info=True)
            return False

# 單例模式實例
conversation_store = ConversationStore() 