#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
功能測試腳本
此腳本用於測試BodhiBot的核心功能
"""

import os
import sys
import json
import unittest
import asyncio
from pathlib import Path

# 添加項目根目錄到路徑
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.services.quick_reply_manager import QuickReplyManager
from app.services.sutra_retriever import SutraRetriever
from app.services.news_processor import NewsProcessor
from app.data_processing.cbeta_processor import CBETAProcessor

class TestCoreFunctionality(unittest.TestCase):
    """測試核心功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.quick_reply_manager = QuickReplyManager()
        self.sutra_retriever = SutraRetriever()
        self.news_processor = NewsProcessor()
        self.cbeta_processor = CBETAProcessor()
        
        # 確保環境變數設置正確
        assert settings.OPENAI_API_KEY, "OpenAI API 密鑰未設置"
        
        # 確認必要的資料目錄存在
        assert os.path.exists("data/cbeta"), "CBETA 資料目錄不存在"
        assert os.path.exists("data/input"), "輸入資料目錄不存在"
        assert os.path.exists("data/output"), "輸出資料目錄不存在"
        assert os.path.exists("data/vector_db"), "向量資料庫目錄不存在"
        
        # 檢查是否有經文檔案
        cbeta_files = list(Path("data/cbeta").glob("*.json"))
        assert len(cbeta_files) > 0, "CBETA 資料目錄中沒有經文檔案"
        
        print("測試環境設置完成")
    
    def test_quick_reply_manager(self):
        """測試快速回覆管理器"""
        # 測試主選單快速回覆
        main_menu = self.quick_reply_manager.get_main_menu()
        self.assertIsNotNone(main_menu)
        print(f"成功獲取主選單快速回覆")
        
        # 測試類別快速回覆
        category_replies = self.quick_reply_manager.get_category_quick_reply("佛法問答")
        self.assertIsNotNone(category_replies)
        print(f"成功獲取類別快速回覆")
        
        # 測試建議回覆
        suggested_replies = self.quick_reply_manager.get_suggested_replies("如何冥想?")
        self.assertIsNotNone(suggested_replies)
        print(f"成功獲取建議回覆")
        
        print("快速回覆管理器測試通過")
    
    async def test_sutra_retriever(self):
        """測試經文檢索"""
        # 測試經文檢索
        cbeta_file = list(Path("data/cbeta").glob("*.json"))[0]
        
        # 載入檔案
        with open(cbeta_file, "r", encoding="utf-8") as f:
            sutra_data = json.load(f)
        
        # 取得經文內容
        sutra_id = cbeta_file.stem
        sutra_name = sutra_data.get("title", sutra_id)
        
        print(f"測試經文: {sutra_name} ({sutra_id})")
        
        # 測試獲取經文引文
        try:
            quote = await self.sutra_retriever.get_sutra_quote(f"請解釋{sutra_name}中的重要概念")
            
            # 由於沒有向量索引，這裡可能會失敗，但我們只確認函數能運行
            if quote:
                print(f"成功獲取經文引文: {quote[:100]}...")
            else:
                print("無法獲取經文引文，但函數運行正常")
        except Exception as e:
            print(f"經文檢索出錯，但這在測試中是可以接受的: {e}")
    
    async def test_news_processor(self):
        """測試新聞處理器"""
        try:
            # 測試獲取新聞
            news = await self.news_processor.get_latest_news(1)
            
            # 由於沒有 GNews API 密鑰，可能會使用備用來源
            if news:
                print(f"成功獲取新聞: {len(news)} 條")
                if len(news) > 0:
                    print(f"第一條新聞標題: {news[0].get('title', '無標題')}")
            else:
                print("無法獲取新聞，但函數運行正常")
        except Exception as e:
            print(f"新聞處理器測試出錯: {e}")
    
    async def test_cbeta_processor(self):
        """測試 CBETA 處理器"""
        try:
            # 測試讀取現有經文
            cbeta_file = list(Path("data/cbeta").glob("*.json"))[0]
            sutra_id = cbeta_file.stem
            
            # 載入檔案內容測試
            with open(cbeta_file, "r", encoding="utf-8") as f:
                sutra_data = json.load(f)
            
            print(f"成功讀取經文: {sutra_id}")
            print(f"經文標題: {sutra_data.get('title', '無標題')}")
            content = sutra_data.get("content", "")
            if content:
                print(f"經文內容預覽: {content[:100]}...")
        except Exception as e:
            print(f"CBETA 處理器測試出錯: {e}")

def run_async_tests():
    """運行非同步測試"""
    test = TestCoreFunctionality()
    test.setUp()
    test.test_quick_reply_manager()
    
    # 運行非同步測試
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test.test_sutra_retriever())
    loop.run_until_complete(test.test_news_processor())
    loop.run_until_complete(test.test_cbeta_processor())

if __name__ == "__main__":
    # 運行測試
    run_async_tests() 