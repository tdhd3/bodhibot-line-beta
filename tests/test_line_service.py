import os
import sys
import unittest
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# 將父級目錄添加到路徑中，這樣才能導入應用程序模組
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager

class TestLineService(unittest.TestCase):
    """測試 LINE Bot 服務功能"""
    
    def test_quick_reply_manager(self):
        """測試快速回覆管理器的功能"""
        print("\n開始測試快速回覆管理器...")
        
        # 測試主選單
        main_menu = quick_reply_manager.get_main_menu()
        self.assertIsNotNone(main_menu)
        self.assertTrue(hasattr(main_menu, 'items'))
        self.assertTrue(len(main_menu.items) > 0)
        print(f"主選單快速回覆選項數: {len(main_menu.items)}")
        
        # 測試類別快速回覆
        categories = ["佛法學習", "生活應用", "修行指導", "佛教新聞"]
        for category in categories:
            category_reply = quick_reply_manager.get_category_quick_reply(category)
            self.assertIsNotNone(category_reply)
            self.assertTrue(hasattr(category_reply, 'items'))
            print(f"類別 '{category}' 快速回覆選項數: {len(category_reply.items)}")
        
        # 測試上下文快速回覆
        test_messages = [
            "如何修習正念冥想?",
            "佛教如何看待生死問題?",
            "如何應對生活中的壓力?"
        ]
        
        for message in test_messages:
            context_reply = quick_reply_manager.get_context_quick_reply(message)
            self.assertIsNotNone(context_reply)
            self.assertTrue(hasattr(context_reply, 'items'))
            print(f"訊息 '{message}' 生成上下文快速回覆選項數: {len(context_reply.items)}")
    
    async def async_test_response_generator(self):
        """測試回應生成器的功能"""
        print("\n開始測試回應生成器...")
        
        # 測試問題列表
        test_questions = [
            "佛教對於不執著的解釋是什麼?",
            "如何在日常生活中實踐正念?",
            "如何處理負面情緒?"
        ]
        
        for question in test_questions:
            # 生成回應
            response = await response_generator.generate_response(
                "test_user_123", 
                question, 
                add_references=True
            )
            
            # 檢查回應結構
            self.assertIsNotNone(response)
            self.assertTrue(isinstance(response, dict))
            self.assertIn("text", response)
            self.assertIn("references", response)
            self.assertIn("suggestions", response)
            
            print(f"問題: '{question}'")
            print(f"回應長度: {len(response['text'])}")
            print(f"引用數量: {len(response['references'])}")
            print(f"建議數量: {len(response['suggestions'])}")
            print("---")
        
        return True
    
    def test_response_generator(self):
        """執行異步回應生成器測試"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(self.async_test_response_generator())
        self.assertTrue(result)
    
    @patch('app.services.response_generator.response_generator._get_chat_completion')
    async def async_test_mock_response(self, mock_chat_completion):
        """使用模擬測試回應生成"""
        print("\n開始模擬測試回應生成...")
        
        # 設置模擬返回值
        mock_response = {
            "response": "這是一個模擬的回應，解釋了佛教的不執著概念。",
            "references": [
                {"sutra": "金剛經", "sutra_id": "T0235", "text": "凡所有相，皆是虛妄。若見諸相非相，即見如來。"},
                {"sutra": "六祖壇經", "sutra_id": "T2008", "text": "不思善，不思惡，正與麼時，那箇是明上座本來面目？"}
            ],
            "suggestions": ["如何修習正念?", "佛教如何看待因果?", "何謂「無常」?"]
        }
        mock_chat_completion.return_value = mock_response
        
        # 測試回應生成
        response = await response_generator.generate_response("test_user_123", "什麼是不執著?")
        
        # 驗證結果
        self.assertEqual(response["text"], mock_response["response"])
        self.assertEqual(len(response["references"]), len(mock_response["references"]))
        self.assertEqual(len(response["suggestions"]), len(mock_response["suggestions"]))
        
        # 驗證模擬函數被調用
        mock_chat_completion.assert_called_once()
        
        print("模擬測試完成，回應生成測試通過")
        return True
    
    def test_mock_response(self):
        """執行模擬回應測試"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(self.async_test_mock_response())
        self.assertTrue(result)

if __name__ == "__main__":
    print("開始執行 LINE Bot 服務功能測試...")
    unittest.main() 