import os
import sys
import unittest
import asyncio
from pathlib import Path

# 將父級目錄添加到路徑中，這樣才能導入應用程序
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.quick_reply_manager import quick_reply_manager
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager
from app.data_processing.cbeta_processor import CBETAProcessor

class TestBasicFunctionality(unittest.TestCase):
    """測試應用程序的基本功能"""
    
    def test_quick_reply_manager(self):
        """測試快速回覆管理器的初始化和基本功能"""
        # 測試主選單功能
        main_menu = quick_reply_manager.get_main_menu()
        self.assertIsNotNone(main_menu)
        
        # 測試類別快速回覆功能
        category_reply = quick_reply_manager.get_category_quick_reply("佛法學習")
        self.assertIsNotNone(category_reply)
        
        # 測試上下文快速回覆功能
        context_reply = quick_reply_manager.get_context_quick_reply("禪修冥想如何幫助我減輕壓力？")
        self.assertIsNotNone(context_reply)
        
        # 測試關鍵詞分類
        category = quick_reply_manager._get_category_by_keywords("四聖諦和八正道有什麼關係？")
        self.assertEqual(category, "佛法學習")
        
        # 測試用戶回饋表單URL
        self.assertTrue(hasattr(quick_reply_manager, 'feedback_form_url'))
        self.assertIsNotNone(quick_reply_manager.feedback_form_url)
    
    async def async_test_news_processor(self):
        """測試新聞處理器的功能"""
        # 測試獲取和格式化新聞
        news_text = await news_processor.get_formatted_news()
        self.assertIsNotNone(news_text)
        self.assertIn("時事省思", news_text)
        return news_text
    
    def test_news_processor(self):
        """執行異步新聞處理器測試"""
        loop = asyncio.get_event_loop()
        news_text = loop.run_until_complete(self.async_test_news_processor())
        print("新聞功能測試成功，獲取到的新聞：")
        print(news_text[:200] + "...")  # 只顯示前200個字符
    
    async def async_test_cbeta_processor(self):
        """測試CBETA處理器的功能（僅測試初始化）"""
        processor = CBETAProcessor()
        self.assertIsNotNone(processor)
        
        # 檢查必要的文件夾是否存在
        cbeta_folder = Path(settings.CBETA_FOLDER)
        self.assertTrue(cbeta_folder.exists())
        
        # 檢查是否可以連接到OpenAI API（如果設置了密鑰）
        if settings.OPENAI_API_KEY:
            self.assertIsNotNone(processor.embeddings)
        
        return processor
    
    def test_cbeta_processor(self):
        """執行異步CBETA處理器測試"""
        loop = asyncio.get_event_loop()
        processor = loop.run_until_complete(self.async_test_cbeta_processor())
        print(f"CBETA處理器初始化成功，支持的經文數量：{len(settings.SUPPORTED_SUTRAS)}")
    
    def test_config(self):
        """測試配置設置"""
        # 檢查模型設置
        self.assertEqual(settings.GPT_MODEL, "gpt-4o-mini")
        
        # 檢查用戶回饋表單URL
        self.assertTrue(hasattr(settings, 'USER_FEEDBACK_FORM'))
        self.assertIsNotNone(settings.USER_FEEDBACK_FORM)
        
        # 檢查支持的經文
        self.assertTrue(len(settings.SUPPORTED_SUTRAS) > 0)
        
        print(f"配置測試成功，使用模型：{settings.GPT_MODEL}")
    
    def test_user_manager(self):
        """測試用戶管理功能"""
        # 測試敏感詞過濾
        content = "這是一個包含賭博相關的問題"
        has_sensitive, filtered_content = user_manager.filter_sensitive_content(content)
        self.assertTrue(has_sensitive)
        self.assertNotEqual(content, filtered_content)
        
        # 測試實例化是否成功
        self.assertIsNotNone(user_manager)
        self.assertTrue(hasattr(user_manager, 'rate_limit'))
        self.assertTrue(hasattr(user_manager, 'history_limit'))
        
        print("用戶管理功能測試成功")
    
    async def async_test_chat_history(self):
        """測試聊天歷史管理功能"""
        test_user_id = "test_user_123"
        
        # 儲存訊息
        await user_manager.store_message(test_user_id, "user", "這是測試訊息")
        
        # 獲取歷史
        history = await user_manager.get_chat_history(test_user_id)
        self.assertTrue(len(history) > 0)
        
        # 清除歷史
        result = await user_manager.clear_chat_history(test_user_id)
        self.assertTrue(result)
        
        # 確認清除成功
        history_after_clear = await user_manager.get_chat_history(test_user_id)
        self.assertEqual(len(history_after_clear), 0)
        
        return True
    
    def test_chat_history(self):
        """執行聊天歷史管理測試"""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.async_test_chat_history())
        self.assertTrue(result)
        print("聊天歷史管理功能測試成功")

if __name__ == '__main__':
    print("開始執行佛教智慧對話系統基本功能測試...")
    unittest.main() 