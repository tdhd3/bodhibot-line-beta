import logging
from sqlalchemy.orm import Session
from linebot import LineBotApi
from linebot.models import TextSendMessage, FlexSendMessage

from app.core.config import settings
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager
from app.db.crud import create_message

# 初始化LINE Bot API
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def format_references(references: list):
    """
    格式化參考資料為LINE Flex Message
    
    Args:
        references: 參考資料列表
    
    Returns:
        Dict: Flex Message數據
    """
    # 此處可以從line_webhook.py複製format_references函數的邏輯
    # 為簡化，這裡返回一個基本的flex message
    bubble_contents = []
    
    # 只顯示至多3個參考資料
    for i, ref in enumerate(references[:3]):
        sutra_name = ref.get("sutra", "佛教經典") if not ref.get("custom", False) else ref.get("source", "參考資料")
        content = ref.get("text", "")[:80] + "..." if len(ref.get("text", "")) > 80 else ref.get("text", "")
        
        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"《{sutra_name}》",
                        "weight": "bold",
                        "color": "#1DB446",
                        "size": "md"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": content,
                        "size": "sm",
                        "wrap": True
                    }
                ]
            }
        }
        bubble_contents.append(bubble)
    
    # 如果沒有引用，添加一個提示氣泡
    if not bubble_contents:
        bubble_contents.append({
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "此回答未引用特定經典",
                        "size": "md",
                        "wrap": True,
                        "align": "center",
                        "color": "#888888"
                    }
                ],
                "paddingAll": "20px"
            }
        })
    
    # 創建Flex Message內容
    return {
        "type": "carousel",
        "contents": bubble_contents
    }

async def process_user_query(db: Session, user, user_message: str, reply_token: str):
    """
    處理用戶一般佛法問答的後台任務
    
    Args:
        db: 資料庫會話
        user: 用戶對象
        user_message: 用戶訊息
        reply_token: LINE回覆令牌
    """
    try:
        # 生成回應
        response_data = await response_generator.generate_response(user_message, user.line_id)
        response_text = response_data["text"]
        references = response_data["references"]
        
        # 存儲機器人回應到資料庫
        create_message(db, user.id, "bot", response_text)
        
        # 應用Markdown格式化，保持簡潔
        formatted_response = quick_reply_manager.format_markdown(response_text)
        
        # 美化回應文本，移除多餘的符號和標記
        formatted_response = formatted_response.replace("\n---\n", "\n" + "----------" + "\n")
        formatted_response = formatted_response.replace("【", "")
        formatted_response = formatted_response.replace("】", "")
        formatted_response = formatted_response.replace("*", "")
        
        # 準備回覆訊息
        messages_to_reply = [
            TextSendMessage(
                text=formatted_response,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        ]
        
        # 如果有引用經文，添加Flex Message
        if references:
            flex_content = await format_references(references)
            flex_message = FlexSendMessage(
                alt_text="相關經文",
                contents=flex_content,
                quick_reply=quick_reply_manager.get_main_menu()
            )
            messages_to_reply.append(flex_message)
        
        # 發送回覆
        line_bot_api.push_message(user.line_id, messages_to_reply)
        
    except Exception as e:
        # 發生錯誤時記錄並發送錯誤消息
        logger.error(f"處理用戶問題時出錯: {e}", exc_info=True)
        error_message = "很抱歉，處理您的問題時發生錯誤。請稍後再試。"
        
        try:
            line_bot_api.push_message(
                user.line_id,
                TextSendMessage(
                    text=error_message,
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            )
        except Exception as push_error:
            logger.error(f"發送錯誤消息時出錯: {push_error}", exc_info=True) 