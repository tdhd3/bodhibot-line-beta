"""
Buddhist bot load testing script
測試系統穩定性和性能的負載測試腳本
"""

import asyncio
import time
import random
import json
import logging
import hmac
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor
import httpx
import os
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("load_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 測試配置
BASE_URL = "http://localhost:8000"  # 根據實際運行的URL調整
TEST_DURATION = 120  # 測試持續時間（秒）
MAX_CONCURRENT_REQUESTS = 8  # 最大併發請求數
WEBHOOK_ENDPOINT = "/api/line/webhook"  # LINE Webhook端點

# LINE配置（從環境變量或配置文件獲取）
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "dummy_secret_for_testing")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy_token_for_testing")

# 測試用戶ID
TEST_USER_IDS = [f"test_user_{i}" for i in range(10)]

# 測試問題池
TEST_QUESTIONS = [
    "什麼是四聖諦？",
    "如何修習慈悲心？",
    "佛教如何看待因果？",
    "如何開始禪修？",
    "金剛經有什麼重要教導？",
    "如何理解無我？",
    "如何面對生活中的苦難？",
    "菩薩道是什麼？",
    "如何培養正念？",
    "佛教對於生死輪迴的看法是什麼？",
    "空性是什麼意思？",
    "如何在現代生活中實踐佛法？",
    "佛教對於心的理解是什麼？",
    "如何處理負面情緒？",
    "什麼是正確的修行方式？"
]

def generate_line_signature(channel_secret, body):
    """
    生成LINE請求的X-Line-Signature
    """
    hash = hmac.new(channel_secret.encode('utf-8'),
                    body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode('utf-8')
    return signature

async def send_message(user_id, message):
    """
    模擬發送LINE訊息並測量響應時間
    """
    # 構建LINE平台的webhook事件格式
    line_event = {
        "destination": "xxxxxxxxxx",
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": f"message_{int(time.time())}",
                    "text": message
                },
                "timestamp": int(time.time() * 1000),
                "source": {
                    "type": "user",
                    "userId": user_id
                },
                "replyToken": f"reply_token_{int(time.time())}",
                "mode": "active"
            }
        ]
    }
    
    # 轉換為JSON字符串
    body = json.dumps(line_event)
    
    # 生成LINE簽名
    signature = generate_line_signature(CHANNEL_SECRET, body)
    
    try:
        start_time = time.time()
        
        # 設置LINE請求頭
        headers = {
            "Content-Type": "application/json",
            "X-Line-Signature": signature,
            "X-Line-Destination": "xxxxxxxxxx",
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}{WEBHOOK_ENDPOINT}",
                content=body,
                headers=headers
            )
            
        end_time = time.time()
        response_time = end_time - start_time
        
        # 檢查回應
        if response.status_code == 200:
            logger.info(f"Request successful - User: {user_id}, Message: '{message}', Response time: {response_time:.2f}s")
            return True, response_time
        else:
            logger.error(f"Request failed - Status: {response.status_code}, User: {user_id}, Message: '{message}', Response: {response.text}")
            return False, response_time
    
    except Exception as e:
        logger.error(f"Error during request - User: {user_id}, Message: '{message}', Error: {str(e)}")
        return False, 0

async def load_test():
    """
    執行負載測試
    """
    logger.info(f"開始負載測試 - 持續時間: {TEST_DURATION}秒, 最大併發請求: {MAX_CONCURRENT_REQUESTS}")
    
    start_time = time.time()
    request_count = 0
    success_count = 0
    total_response_time = 0
    
    # 併發請求池
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def controlled_request():
        nonlocal request_count, success_count, total_response_time
        async with semaphore:
            user_id = random.choice(TEST_USER_IDS)
            
            # 用戶最初問候
            greeting = random.choice([
                "你好",
                "嗨，請問一下",
                "請教一個問題",
                "我想了解佛法",
                "可以請教一個問題嗎"
            ])
            
            request_count += 1
            success, response_time = await send_message(user_id, greeting)
            if success:
                success_count += 1
                total_response_time += response_time
                
                # 短暫延遲，模擬用戶思考時間
                await asyncio.sleep(random.uniform(1, 3))
                
                # 用戶提出正式問題
                question = random.choice(TEST_QUESTIONS)
                request_count += 1
                success, response_time = await send_message(user_id, question)
                if success:
                    success_count += 1
                    total_response_time += response_time
                
                # 繼續對話 (根據前面問題生成後續問題)
                if random.random() < 0.7:  # 70%的機率繼續對話
                    await asyncio.sleep(random.uniform(2, 5))
                    followup_questions = [
                        f"能解釋得再詳細一點嗎？",
                        f"有什麼經典提到這個觀點？",
                        f"這和{random.choice(['慈悲心', '正念', '智慧', '因果'])}有什麼關係？",
                        f"如何在日常生活中實踐這個教導？"
                    ]
                    request_count += 1
                    success, response_time = await send_message(user_id, random.choice(followup_questions))
                    if success:
                        success_count += 1
                        total_response_time += response_time
    
    # 持續發送請求直到測試時間結束
    tasks = []
    while time.time() - start_time < TEST_DURATION:
        # 創建新的請求任務
        task = asyncio.create_task(controlled_request())
        tasks.append(task)
        
        # 控制請求頻率
        await asyncio.sleep(random.uniform(0.5, 2.0))
    
    # 等待所有任務完成
    if tasks:
        await asyncio.gather(*tasks)
    
    # 計算測試結果
    end_time = time.time()
    test_duration = end_time - start_time
    
    logger.info(f"負載測試完成 - 總時間: {test_duration:.2f}秒")
    logger.info(f"總請求數: {request_count}")
    logger.info(f"成功請求數: {success_count}")
    logger.info(f"成功率: {(success_count/request_count)*100 if request_count else 0:.2f}%")
    
    if success_count > 0:
        logger.info(f"平均響應時間: {total_response_time/success_count:.2f}秒")

if __name__ == "__main__":
    asyncio.run(load_test()) 