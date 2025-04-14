import logging
from typing import Dict, Any
import json

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage, QuickReply, QuickReplyButton, 
    MessageAction
)

from app.core.config import settings
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化LINE Bot API
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

def format_references(references: list) -> Dict[str, Any]:
    """
    格式化引用的經文為LINE Flex Message格式
    
    Args:
        references: 引用的經文列表
        
    Returns:
        Dict: Flex Message內容
    """
    bubble_contents = []
    
    for ref in references:
        # 根據參考來源類型建立不同的氣泡
        if ref.get("custom", False):
            # 自定義文檔
            bubble = {
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"《{ref['source']}》",
                            "weight": "bold",
                            "size": settings.FONT_SIZE_MEDIUM,
                            "color": settings.THEME_COLOR
                        }
                    ],
                    "backgroundColor": "#F8F8F8"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": ref["text"][:100] + "..." if len(ref["text"]) > 100 else ref["text"],
                            "size": settings.FONT_SIZE_SMALL,
                            "wrap": True,
                            "style": "italic",
                            "color": "#555555"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px"
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "自定義文檔",
                            "size": "xs",
                            "color": "#aaaaaa",
                            "align": "center"
                        }
                    ],
                    "paddingAll": "8px"
                },
                "styles": {
                    "header": {
                        "separator": True
                    },
                    "footer": {
                        "separator": True
                    }
                }
            }
        else:
            # CBETA經文
            bubble = {
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"《{ref['sutra']}》",
                            "weight": "bold",
                            "size": settings.FONT_SIZE_MEDIUM,
                            "color": settings.THEME_COLOR
                        }
                    ],
                    "backgroundColor": "#F8F8F8"
                },
                "hero": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📜 經典引用",
                            "align": "center",
                            "color": "#888888",
                            "size": "xs"
                        }
                    ],
                    "paddingAll": "8px",
                    "backgroundColor": "#F1F1F1"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": ref["text"][:100] + "..." if len(ref["text"]) > 100 else ref["text"],
                            "size": settings.FONT_SIZE_SMALL,
                            "wrap": True,
                            "style": "italic",
                            "color": "#555555"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "text",
                            "text": f"CBETA ID: {ref['sutra_id']}",
                            "size": "xs",
                            "color": "#aaaaaa",
                            "margin": "md"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px"
                },
                "styles": {
                    "header": {
                        "separator": True
                    }
                }
            }
        
        bubble_contents.append(bubble)
    
    # 如果沒有引用，添加一個默認氣泡
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
                        "text": "未找到相關經文",
                        "size": settings.FONT_SIZE_MEDIUM,
                        "wrap": True,
                        "align": "center",
                        "color": "#888888"
                    },
                    {
                        "type": "icon",
                        "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gray_star_28.png",
                        "size": "xl",
                        "margin": "md",
                        "offsetTop": "sm",
                        "offsetStart": "0px"
                    }
                ],
                "paddingAll": "20px"
            }
        })
    
    # 創建Flex Message內容
    flex_content = {
        "type": "carousel",
        "contents": bubble_contents
    }
    
    return flex_content

async def handle_text_message(event: MessageEvent) -> None:
    """
    處理文字訊息事件
    
    Args:
        event: LINE訊息事件
    """
    user_id = event.source.user_id
    user_message = event.message.text
    
    # 檢查用戶是否可以發送新問題 (是否正在等待回答)
    if not await user_manager.check_user_can_send(user_id) and user_message != "清除對話記錄":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="您的上一個問題正在處理中，請等待回答後再提問。如需重新開始，請輸入「清除對話記錄」。",
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 檢查請求頻率限制
    if not await user_manager.check_rate_limit(user_id):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="您的訊息發送過於頻繁，請稍後再試。",
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 過濾敏感內容
    has_sensitive, filtered_message = user_manager.filter_sensitive_content(user_message)
    if has_sensitive:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="您的訊息包含不適當內容，已被過濾。我們鼓勵健康、正面的交流。",
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 存儲用戶訊息到對話歷史
    await user_manager.store_message(user_id, "user", user_message)
    
    # 特殊指令處理
    if user_message == "清除對話記錄":
        response = quick_reply_manager.handle_clear_history(user_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=quick_reply_manager.get_main_menu())
        )
        return
    
    # 主選單處理
    if user_message == "主選單":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="您好，請選擇您想了解的主題：",
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 類別選單處理
    if user_message in quick_reply_manager.quick_replies:
        category = user_message
        intro_text = f"關於「{category}」，您可以問以下問題："
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=intro_text,
                quick_reply=quick_reply_manager.get_category_quick_reply(category)
            )
        )
        return
    
    # 時事省思處理
    if user_message == "時事省思":
        news_text = await news_processor.get_formatted_news()
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=news_text,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 禪修引導處理
    if user_message == "禪修引導":
        # 這裡可以添加實際的禪修引導功能
        meditation_text = "請找一個安靜的地方坐下，保持背部挺直，放鬆肩膀。\n\n" \
                        "閉上眼睛，將注意力放在呼吸上。\n\n" \
                        "當你吸氣時，感受空氣進入鼻孔，通過喉嚨，充滿胸腔。\n\n" \
                        "當你呼氣時，感受空氣離開身體的過程。\n\n" \
                        "如果心念飄走，溫柔地將注意力帶回呼吸。\n\n" \
                        "就這樣保持5-10分鐘，培養當下的覺知。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=meditation_text,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 系統功能處理
    if user_message == "系統功能":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="請選擇系統功能：",
                quick_reply=quick_reply_manager.get_category_quick_reply("系統")
            )
        )
        return
    
    # 使用回饋處理
    if user_message == "提供使用回饋":
        response = quick_reply_manager.handle_feedback_request()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=quick_reply_manager.get_main_menu())
        )
        return
    
    # 使用說明處理
    if user_message == "查看使用說明":
        help_text = "【佛教智慧對話系統使用說明】\n\n" \
                  "• 您可以直接提問佛法相關問題\n" \
                  "• 使用「主選單」進入功能選單\n" \
                  "• 「時事省思」提供佛法視角的新聞觀點\n" \
                  "• 「禪修引導」提供冥想指導\n" \
                  "• 「清除對話記錄」重置對話\n\n" \
                  "本系統基於唯識學與語意檢索，為您提供適合的佛法智慧。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=help_text,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        return
    
    # 生成回應
    response_data = await response_generator.generate_response(user_message, user_id)
    response_text = response_data["text"]
    references = response_data["references"]
    
    # 存儲機器人回應到對話歷史
    await user_manager.store_message(user_id, "assistant", response_text)
    
    # 應用Markdown格式化
    formatted_response = quick_reply_manager.format_markdown(response_text)
    
    # 根據內容智能選擇快速回覆
    context_quick_reply = quick_reply_manager.get_context_quick_reply(user_message + " " + response_text)
    
    # 美化回應文本中的分隔線
    formatted_response = formatted_response.replace("\n---\n", "\n" + "⎯" * 15 + "\n")
    
    # 添加視覺化標記
    if "佛陀" in formatted_response:
        formatted_response = formatted_response.replace("佛陀", "🙏 佛陀")
    if "禪修" in formatted_response:
        formatted_response = formatted_response.replace("禪修", "🧘 禪修")
    if "冥想" in formatted_response:
        formatted_response = formatted_response.replace("冥想", "🧘‍♂️ 冥想")
    if "經典" in formatted_response:
        formatted_response = formatted_response.replace("經典", "📜 經典")
    
    # 添加視覺區塊標識
    if "第一步" in formatted_response:
        formatted_response = formatted_response.replace("第一步", "1️⃣ 第一步")
    if "第二步" in formatted_response:
        formatted_response = formatted_response.replace("第二步", "2️⃣ 第二步")
    if "第三步" in formatted_response:
        formatted_response = formatted_response.replace("第三步", "3️⃣ 第三步")
    
    # 回覆主要訊息
    messages_to_reply = [
        # 主要回應文本
        TextSendMessage(text=formatted_response, quick_reply=context_quick_reply)
    ]
    
    # 如果有引用經文，添加Flex Message
    if references:
        messages_to_reply.append(
            FlexSendMessage(
                alt_text="相關經文",
                contents=format_references(references)
            )
        )
    
    # 發送回覆
    line_bot_api.reply_message(event.reply_token, messages_to_reply)

@router.post(settings.WEBHOOK_PATH)
async def line_webhook(request: Request):
    """
    LINE Webhook 處理器
    接收來自LINE平台的事件通知，並進行處理
    """
    # 獲取請求頭部的簽名
    signature = request.headers.get('X-Line-Signature', '')
    
    # 獲取請求體
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # 驗證簽名
    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.error("無效的簽名")
        raise HTTPException(status_code=400, detail="無效的簽名")
    
    return 'OK'

@router.post("/chat")
async def manual_chat(request: Request):
    """
    手動觸發聊天（用於測試）
    
    Args:
        request: HTTP請求物件
        
    Returns:
        Dict: 回應數據
    """
    try:
        data = await request.json()
        user_message = data.get("message", "")
        user_id = data.get("user_id", "test_user")
        
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "缺少訊息內容"}
            )
        
        # 生成回應
        response_data = await response_generator.generate_response(user_message, user_id)
        
        # 獲取適合的快速回覆建議
        suggested_replies = quick_reply_manager.get_suggested_replies(user_message)
        
        return {
            "status": "success",
            "response": response_data["text"],
            "references": response_data["references"],
            "user_level": response_data["user_level"],
            "issue_type": response_data["issue_type"],
            "four_she_strategy": response_data["four_she_strategy"],
            "suggested_replies": suggested_replies
        }
        
    except Exception as e:
        logger.error(f"手動聊天時出錯: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@router.get("/news")
async def get_news():
    """
    獲取每日新聞省思（用於測試）
    
    Returns:
        Dict: 新聞數據
    """
    try:
        news_text = await news_processor.get_formatted_news()
        
        return {
            "status": "success",
            "news": news_text
        }
    except Exception as e:
        logger.error(f"獲取新聞時出錯: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        ) 