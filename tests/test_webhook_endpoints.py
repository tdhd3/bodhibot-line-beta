import os
import sys
import unittest
import json
from fastapi.testclient import TestClient

# 將父級目錄添加到路徑中，以便導入應用程序
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

class TestWebhookEndpoints(unittest.TestCase):
    """測試 webhook 端點"""
    
    def setUp(self):
        self.client = TestClient(app)
        self.test_event = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "test_reply_token",
                    "source": {"type": "user", "userId": "test_user_123"},
                    "timestamp": 1234567890123,
                    "message": {"type": "text", "id": "12345", "text": "測試訊息"}
                }
            ]
        }
        # 模擬 LINE 簽名
        self.headers = {"X-Line-Signature": "dummy_signature"}
    
    def test_direct_webhook_endpoint(self):
        """測試直接的 webhook 端點"""
        print("\n正在測試直接的 webhook 端點 '/webhook'...")
        
        response = self.client.post(
            "/webhook", 
            json=self.test_event, 
            headers=self.headers
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.text}")
        
        # 檢查狀態碼，即使簽名驗證失敗也可以確認端點存在
        self.assertIn(response.status_code, [200, 400])
    
    def test_nested_webhook_endpoint(self):
        """測試嵌套的 webhook 端點"""
        print("\n正在測試嵌套的 webhook 端點 '/api/line/webhook'...")
        
        response = self.client.post(
            "/api/line/webhook", 
            json=self.test_event, 
            headers=self.headers
        )
        
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.text}")
        
        # 檢查狀態碼，即使簽名驗證失敗也可以確認端點存在
        self.assertIn(response.status_code, [200, 400])
    
    def test_health_endpoint(self):
        """測試健康檢查端點"""
        print("\n正在測試健康檢查端點 '/health'...")
        
        response = self.client.get("/health")
        
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

if __name__ == "__main__":
    print("開始測試 webhook 端點...")
    unittest.main() 