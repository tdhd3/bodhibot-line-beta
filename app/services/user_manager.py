import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class UserManager:
    """
    用戶管理服務
    負責用戶的對話歷史存儲、清除以及請求頻率限制
    """
    
    def __init__(self):
        """初始化用戶管理服務"""
        # 使用內存存儲
        self.local_storage = {}
        
        # 用戶狀態追蹤 - 用於確保每次只能有一個問題在處理中
        # 可能的狀態: 'idle'(空閒), 'processing'(處理中)
        self.user_status = {}
        
        # 敏感詞列表 (簡單示例，實際應用可能需要更全面的列表)
        self.sensitive_words = [
            "色情", "賭博", "毒品", "自殺", "暴力", "違法", "恐怖", 
            "種族歧視", "政治敏感", "淫穢", "赤裸", "裸露", "情色"
        ]
        
        # 請求頻率限制配置
        self.rate_limit = {
            "window_seconds": 60,  # 60秒窗口期
            "max_requests": 10      # 最多允許10個請求
        }
        
        # 對話歷史上限
        self.history_limit = settings.HISTORY_LIMIT
        
        logger.info("UserManager 初始化完成")
    
    async def set_user_status(self, user_id: str, status: str) -> None:
        """
        設置用戶狀態
        
        Args:
            user_id: 用戶ID
            status: 狀態 ('idle' 或 'processing')
        """
        self.user_status[user_id] = {
            'status': status,
            'timestamp': datetime.now().timestamp()
        }
        logger.info(f"用戶 {user_id} 狀態設置為 {status}")
    
    async def get_user_status(self, user_id: str) -> str:
        """
        獲取用戶狀態
        
        Args:
            user_id: 用戶ID
            
        Returns:
            str: 用戶狀態，如果沒有記錄則返回 'idle'
        """
        if user_id not in self.user_status:
            return 'idle'
        
        # 檢查是否過期 (防止因為某些原因，狀態未被重置)
        status_data = self.user_status[user_id]
        current_time = datetime.now().timestamp()
        
        # 如果狀態設置時間超過5分鐘，自動重置為空閒
        if current_time - status_data['timestamp'] > 300:  # 5分鐘超時
            await self.set_user_status(user_id, 'idle')
            return 'idle'
            
        return status_data['status']
    
    async def check_user_can_send(self, user_id: str) -> bool:
        """
        檢查用戶是否可以發送新問題
        
        Args:
            user_id: 用戶ID
            
        Returns:
            bool: 如果用戶可以發送新問題返回True，否則返回False
        """
        status = await self.get_user_status(user_id)
        return status == 'idle'
    
    async def store_message(self, user_id: str, role: str, content: str) -> bool:
        """
        存儲用戶的對話消息
        
        Args:
            user_id: 用戶ID
            role: 消息角色 (user或assistant)
            content: 消息內容
            
        Returns:
            bool: 存儲成功返回True，否則返回False
        """
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 使用本地存儲，確保正確初始化所有必要的字段
            if user_id not in self.local_storage:
                self.local_storage[user_id] = {
                    "chat_history": [],
                    "request_timestamps": []
                }
            elif "chat_history" not in self.local_storage[user_id]:
                self.local_storage[user_id]["chat_history"] = []
            
            self.local_storage[user_id]["chat_history"].append(message)
            
            # 限制歷史記錄數量
            if len(self.local_storage[user_id]["chat_history"]) > self.history_limit * 2:
                self.local_storage[user_id]["chat_history"] = self.local_storage[user_id]["chat_history"][-self.history_limit * 2:]
            
            # 更新用戶狀態
            if role == "user":
                # 用戶發送消息時，將狀態設置為處理中
                await self.set_user_status(user_id, 'processing')
            elif role == "assistant":
                # AI回答後，將狀態設置為空閒
                await self.set_user_status(user_id, 'idle')
            
            return True
        except Exception as e:
            logger.error(f"存儲消息時發生錯誤: {str(e)}")
            return False
    
    async def get_chat_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取用戶的對話歷史
        
        Args:
            user_id: 用戶ID
            
        Returns:
            List: 對話歷史列表
        """
        try:
            # 從本地存儲獲取
            if user_id in self.local_storage and "chat_history" in self.local_storage[user_id]:
                return self.local_storage[user_id]["chat_history"]
            else:
                return []
        except Exception as e:
            logger.error(f"獲取對話歷史時發生錯誤: {str(e)}")
            return []
    
    async def clear_chat_history(self, user_id: str) -> bool:
        """
        清除用戶的對話歷史
        
        Args:
            user_id: 用戶ID
            
        Returns:
            bool: 清除成功返回True，否則返回False
        """
        try:
            # 從本地存儲刪除
            if user_id in self.local_storage:
                self.local_storage[user_id]["chat_history"] = []
            
            # 重置用戶狀態為空閒
            await self.set_user_status(user_id, 'idle')
            
            logger.info(f"已清除用戶 {user_id} 的對話歷史")
            return True
        except Exception as e:
            logger.error(f"清除對話歷史時發生錯誤: {str(e)}")
            return False
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        檢查用戶請求頻率是否超過限制
        
        Args:
            user_id: 用戶ID
            
        Returns:
            bool: 未超過限制返回True，否則返回False
        """
        try:
            current_time = int(time.time())
            window_start = current_time - self.rate_limit["window_seconds"]
            
            # 使用本地存儲
            if user_id not in self.local_storage:
                self.local_storage[user_id] = {
                    "chat_history": [],
                    "request_timestamps": []
                }
            elif "request_timestamps" not in self.local_storage[user_id]:
                self.local_storage[user_id]["request_timestamps"] = []
            
            # 添加當前請求時間戳
            self.local_storage[user_id]["request_timestamps"].append(current_time)
            
            # 刪除窗口期以外的時間戳
            self.local_storage[user_id]["request_timestamps"] = [
                ts for ts in self.local_storage[user_id]["request_timestamps"]
                if ts > window_start
            ]
            
            # 獲取窗口期內的請求數
            request_count = len(self.local_storage[user_id]["request_timestamps"])
            
            # 檢查是否超過限制
            if request_count > self.rate_limit["max_requests"]:
                logger.warning(f"用戶 {user_id} 請求頻率超過限制: {request_count}/{self.rate_limit['max_requests']}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"檢查請求頻率時發生錯誤: {str(e)}")
            # 發生錯誤時默認允許請求通過
            return True
    
    def filter_sensitive_content(self, content: str) -> tuple:
        """
        過濾敏感內容
        
        Args:
            content: 要過濾的內容
            
        Returns:
            tuple: (是否包含敏感詞, 過濾後的內容)
        """
        try:
            has_sensitive = False
            filtered_content = content
            
            # 檢查敏感詞
            for word in self.sensitive_words:
                if word in content:
                    has_sensitive = True
                    # 替換敏感詞為星號
                    filtered_content = filtered_content.replace(word, "*" * len(word))
            
            return has_sensitive, filtered_content
        except Exception as e:
            logger.error(f"過濾敏感內容時發生錯誤: {str(e)}")
            return False, content

# 單例模式實例
user_manager = UserManager() 