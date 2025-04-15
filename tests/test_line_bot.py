import sys
import os
import requests
import json
from app.core.config import settings
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 將父級目錄添加到路徑中，這樣才能導入應用程序模組
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_line_connection():
    """測試與LINE API的連接"""
    print("開始測試與LINE API的連接...")
    
    # 初始化LINE Bot API
    line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
    
    try:
        # 獲取Bot自己的個人資料來測試連接
        profile = line_bot_api.get_bot_info()
        print(f"連接成功! Bot名稱: {profile.display_name}")
        print(f"Bot圖像URL: {profile.picture_url if hasattr(profile, 'picture_url') else '無圖像'}")
        return True
        
    except Exception as e:
        print(f"連接失敗: {e}")
        return False

def test_webhook_connection():
    """測試本地webhook伺服器連接"""
    print("\n開始測試本地webhook伺服器連接...")
    
    try:
        # 測試健康檢查端點
        health_response = requests.get("http://localhost:8000/health")
        if health_response.status_code == 200:
            print(f"健康檢查端點連接成功! 響應: {health_response.json()}")
        else:
            print(f"健康檢查端點連接失敗! 狀態碼: {health_response.status_code}")
            return False
        
        # 測試根端點
        root_response = requests.get("http://localhost:8000/")
        if root_response.status_code == 200:
            print(f"根端點連接成功! 響應: {root_response.json()}")
        else:
            print(f"根端點連接失敗! 狀態碼: {root_response.status_code}")
            return False
            
        return True
    except Exception as e:
        print(f"伺服器連接測試失敗: {e}")
        return False

def test_manual_chat():
    """測試手動聊天API端點"""
    print("\n開始測試手動聊天API...")
    
    # 準備請求
    url = "http://localhost:8000/api/line/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "user_id": "test_user_123",
        "message": "南無阿彌陀佛"
    }
    
    try:
        # 發送請求
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            print(f"手動聊天API測試成功! 回應: {response.json()}")
            return True
        else:
            print(f"手動聊天API測試失敗! 狀態碼: {response.status_code}")
            print(f"回應: {response.text}")
            return False
    except Exception as e:
        print(f"手動聊天API測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("===== LINE Bot 連接測試開始 =====")
    
    # 測試 LINE API 連接
    line_connection = test_line_connection()
    
    # 測試 Webhook 伺服器連接
    webhook_connection = test_webhook_connection()
    
    # 測試手動聊天 API
    chat_api = test_manual_chat()
    
    # 測試總結
    print("\n===== 測試結果摘要 =====")
    print(f"LINE API 連接: {'成功 ✓' if line_connection else '失敗 ✗'}")
    print(f"Webhook 伺服器連接: {'成功 ✓' if webhook_connection else '失敗 ✗'}")
    print(f"手動聊天 API: {'成功 ✓' if chat_api else '失敗 ✗'}")
    
    if line_connection and webhook_connection and chat_api:
        print("\n所有測試已通過，LINE Bot 系統已準備就緒! ✓")
    else:
        print("\n部分測試失敗，請檢查上述錯誤並修復問題。")

if __name__ == "__main__":
    main() 