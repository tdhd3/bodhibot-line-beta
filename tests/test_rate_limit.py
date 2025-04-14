import unittest
import asyncio
import sys
import os
from datetime import datetime

# 將父級目錄添加到路徑中，這樣才能導入應用程序
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.user_manager import user_manager

class TestRateLimit(unittest.TestCase):
    """測試請求頻率限制功能"""
    
    def test_rate_limit(self):
        """測試頻率限制功能"""
        test_user_id = f"test_user_{datetime.now().timestamp()}"
        
        async def run_test():
            # 測試沒有超過限制的情況
            for i in range(user_manager.rate_limit["max_requests"]):
                result = await user_manager.check_rate_limit(test_user_id)
                self.assertTrue(result, f"第{i+1}個請求應該通過")
            
            # 測試超過限制的情況
            result = await user_manager.check_rate_limit(test_user_id)
            self.assertFalse(result, "超過限制的請求應該被阻止")
        
        # 執行異步測試
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())
    
    def test_filter_sensitive_content(self):
        """測試敏感詞過濾功能"""
        # 測試不包含敏感詞的情況
        normal_content = "這是一個正常的佛教問題，關於六祖壇經"
        has_sensitive, filtered = user_manager.filter_sensitive_content(normal_content)
        self.assertFalse(has_sensitive, "正常內容不應被標記為敏感")
        self.assertEqual(filtered, normal_content, "正常內容不應被過濾")
        
        # 測試包含敏感詞的情況
        sensitive_content = "這個問題包含色情和賭博內容"
        has_sensitive, filtered = user_manager.filter_sensitive_content(sensitive_content)
        self.assertTrue(has_sensitive, "包含敏感詞的內容應被標記為敏感")
        self.assertNotEqual(filtered, sensitive_content, "敏感內容應被過濾")
        self.assertEqual(filtered, "這個問題包含**和**內容", "敏感詞應被替換為星號")
    
    def test_chat_history(self):
        """測試對話歷史管理功能"""
        test_user_id = f"test_user_{datetime.now().timestamp()}"
        
        async def run_history_test():
            # 測試存儲和獲取
            await user_manager.store_message(test_user_id, "user", "這是用戶消息")
            await user_manager.store_message(test_user_id, "assistant", "這是機器人回應")
            
            history = await user_manager.get_chat_history(test_user_id)
            self.assertEqual(len(history), 2, "應該有兩條歷史記錄")
            self.assertEqual(history[0]["role"], "user", "第一條記錄應為用戶消息")
            self.assertEqual(history[1]["role"], "assistant", "第二條記錄應為機器人回應")
            
            # 測試清除歷史
            success = await user_manager.clear_chat_history(test_user_id)
            self.assertTrue(success, "清除歷史應成功")
            
            history_after_clear = await user_manager.get_chat_history(test_user_id)
            self.assertEqual(len(history_after_clear), 0, "清除後歷史記錄應為空")
        
        # 執行異步測試
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_history_test())

if __name__ == '__main__':
    print("開始測試請求頻率限制和對話歷史管理功能...")
    unittest.main() 