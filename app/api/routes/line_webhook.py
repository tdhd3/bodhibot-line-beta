import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
from datetime import datetime
import re

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookParser, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage, QuickReply, QuickReplyButton, 
    MessageAction, URIAction, PostbackAction
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.response_generator import response_generator
from app.services.quick_reply_manager import quick_reply_manager
from app.services.news_processor import news_processor
from app.services.user_manager import user_manager
from app.db.database import get_db
from app.db.crud import get_user_by_line_id, create_user, create_message
from app.services.query_processor import process_user_query
from app.services.sutra_retriever import sutra_retriever
from app.services.sutra_recommender import sutra_recommender

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化LINE Bot API
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

# 初始化訊息
init_messages = [
    {
        "type": "text",
        "text": "歡迎使用「菩薩小老師」！\n\n我能解答佛法相關問題，提供修行指導，並融合唯識學智慧。請隨時向我提問，讓佛法帶來心靈的平靜與智慧。"
    },
    {
        "type": "text", 
        "text": "您可以這樣問我：\n- 如何面對工作壓力？\n- 唯識學如何解釋妄念？\n- 我該如何開始修行？\n- 如何理解「緣起性空」？"
    }
]

# 確保所有消息都有快速回覆選項
def ensure_quick_replies(messages: List[Union[TextSendMessage, FlexSendMessage]]) -> List[Union[TextSendMessage, FlexSendMessage]]:
    """
    確保所有消息都有快速回覆選項
    
    Args:
        messages: 消息列表
        
    Returns:
        添加了快速回覆選項的消息列表
    """
    for i, message in enumerate(messages):
        # 檢查消息是否已有快速回覆，如果沒有則添加默認快速回覆
        if not hasattr(message, 'quick_reply') or message.quick_reply is None:
            messages[i].quick_reply = quick_reply_manager.get_main_menu()
    
    return messages

def format_references(references: list) -> Dict[str, Any]:
    """
    格式化參考資料為LINE Flex Message，更簡潔明了
    
    Args:
        references: 參考資料列表
    
    Returns:
        Dict: Flex Message數據
    """
    bubble_contents = []
    
    # 根據相關性排序所有參考資料，確保最相關的在最前面
    sorted_references = sorted(
        references, 
        key=lambda x: x.get("relevance", 0) if x.get("relevance") is not None else (
            0.9 if x.get("is_direct_quote", False) else 0.7
        ), 
        reverse=True
    )
    
    # 只顯示相關性最高的3個引用
    processed_references = sorted_references[:3]
    
    for i, ref in enumerate(processed_references):
        # 檢查是否為自定義文檔還是CBETA經文
        if ref.get("custom_document", False) or ref.get("custom", False):
            # 自定義文檔
            source_name = ref.get('source', '參考資料')
            
            bubble = {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"《{source_name}》",
                            "weight": "bold",
                            "color": "#1DB446",
                            "size": settings.FONT_SIZE_MEDIUM
                        }
                    ],
                    "paddingBottom": "8px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": ref.get("text", "")[:150] + "..." if len(ref.get("text", "")) > 150 else ref.get("text", ""),
                            "size": settings.FONT_SIZE_SMALL,
                            "wrap": True,
                            "color": "#555555"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px"
                }
            }
        else:
            # CBETA經文
            sutra_name = ref.get("sutra", "佛教經典")
            sutra_id = ref.get("sutra_id", "")
            
            # CBETA經文連結
            cbeta_url = f"https://cbetaonline.dila.edu.tw/zh/{sutra_id}" if sutra_id else "https://cbetaonline.dila.edu.tw/"
            
            # 提取文本內容，顯示經文片段
            text_content = ref.get("text", "")
            content_to_show = text_content
            
            # 移除sutra_name中可能的書名號，避免重複
            clean_sutra_name = sutra_name.replace('《', '').replace('》', '')
            
            bubble = {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"《{clean_sutra_name}》",
                            "weight": "bold",
                            "color": "#1DB446",
                            "size": settings.FONT_SIZE_MEDIUM
                        }
                    ],
                    "paddingBottom": "8px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"原文：「{content_to_show}」",
                            "size": settings.FONT_SIZE_SMALL,
                            "wrap": True,
                            "color": "#555555"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "button",
                                    "action": {
                                        "type": "uri",
                                        "label": f"CBETA {sutra_id} - 點此查看完整經文",
                                        "uri": cbeta_url
                                    },
                                    "style": "link",
                                    "color": "#1DB446",
                                    "height": "sm"
                                }
                            ]
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px"
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
                        "size": settings.FONT_SIZE_MEDIUM,
                        "wrap": True,
                        "align": "center",
                        "color": "#aaaaaa"
                    }
                ],
                "paddingAll": "12px"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "訪問CBETA佛典網站",
                            "uri": "https://cbetaonline.dila.edu.tw/"
                        },
                        "style": "primary",
                        "color": "#1DB446"
                    }
                ]
            }
        })
    
    # 創建Flex Message內容
    flex_content = {
        "type": "carousel",
        "contents": bubble_contents
    }
    
    return flex_content

async def handle_text_message(event):
    """處理文本消息"""
    user_id = event.source.user_id
    user_message = event.message.text
    
    # 特殊指令處理 - 清除對話記錄必須始終可用，即使在處理其他消息時
    if user_message == "清除對話記錄":
        try:
            # 創建確認按鈕的Flex Message
            flex_content = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "確認清除對話記錄",
                            "weight": "bold",
                            "size": settings.FONT_SIZE_LARGE,
                            "color": "#1DB446",
                            "align": "center"
                        },
                        {
                            "type": "text",
                            "text": "您確定要清除所有對話記錄嗎？這個操作無法撤銷。",
                            "wrap": True,
                            "size": settings.FONT_SIZE_MEDIUM,
                            "margin": "md",
                            "color": "#555555"
                        }
                    ],
                    "paddingAll": "15px"
                },
                "footer": {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "取消",
                                "text": "取消清除"
                            },
                            "style": "secondary",
                            "height": "sm"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "確認清除",
                                "text": "確認清除記錄"
                            },
                            "style": "primary",
                            "color": settings.THEME_COLOR,
                            "height": "sm"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px"
                }
            }
            
            # 確保添加明確的快速回覆選項
            flex_message = FlexSendMessage(
                alt_text="確認清除對話記錄",
                contents=flex_content,
                quick_reply=quick_reply_manager.get_main_menu()
            )
            
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([flex_message])
            )
            
            return
        except Exception as e:
            logger.error(f"處理清除記錄確認時發生錯誤: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="處理清除記錄確認時發生錯誤，請稍後再試。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            )
            return
    
    # 處理確認清除記錄
    if user_message == "確認清除記錄":
        try:
            # 直接重置用戶狀態為空閒，無論當前狀態如何
            await user_manager.set_user_status(user_id, 'idle')
            # 清除對話歷史
            success = await user_manager.clear_chat_history(user_id)
            response_message = "已成功清除所有對話記錄並重置系統狀態。您可以開始新的對話。"
            
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(text=response_message, quick_reply=quick_reply_manager.get_main_menu())
                ])
            )
            return
        except Exception as e:
            logger.error(f"清除對話記錄時發生錯誤: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text="清除對話記錄時發生錯誤，請稍後再試。",
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
            return
            
    # 處理取消清除
    if user_message == "取消清除":
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text="已取消清除對話記錄操作。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        return
    
    # 處理時事省思請求
    if user_message == "時事省思":
        try:
            # 設置用戶狀態為處理中
            await user_manager.set_user_status(user_id, "processing")
            
            # 傳送「處理中」的提示
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="正在獲取時事新聞省思，請稍候...")
            )
            
            # 獲取時事省思內容
            news_text = await news_processor.get_formatted_news()
            
            # 儲存回應到對話歷史
            await user_manager.store_message(user_id, "assistant", "已為您提供今日時事省思")
            
            # 發送回覆
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text=news_text,
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        except Exception as e:
            logger.error(f"獲取時事省思時出錯: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text="很抱歉，獲取今日時事省思時發生錯誤，請稍後再試。",
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        finally:
            # 重置用戶狀態為閒置
            await user_manager.set_user_status(user_id, "idle")
        return
    
    # 處理使用方式請求
    if user_message == "使用方式":
        try:
            # 獲取使用指南
            usage_guide = quick_reply_manager.handle_usage_guide()
            
            # 儲存回應到對話歷史
            await user_manager.store_message(user_id, "assistant", "已為您提供使用指南")
            
            # 發送回覆
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text=usage_guide,
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        except Exception as e:
            logger.error(f"獲取使用指南時出錯: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text="很抱歉，獲取使用指南時發生錯誤，請稍後再試。",
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        return
    
    # 處理禪修引導請求
    if user_message == "禪修引導":
        try:
            # 禪修引導內容
            meditation_guide = """🧘‍♀️ 禪修引導

讓我們開始一個簡短的正念禪修練習：

1. 找一個安靜的地方，保持舒適的正坐姿態
2. 稍微閉上眼睛，將注意力放在呼吸上，可以數1~10或持念佛號
3. 自然地呼氣和吸氣，不需刻意調整，觀察呼吸之間的短暫空白
4. 如果分心，覺察它，並將注意力回到呼吸
5. 持續5-10分鐘，體驗當下的平靜

透過定期禪修，我們可以培養覺知力，減少煩惱，擁有清明的心。

願您在禪修中找到內在的寧靜與智慧。

【經典參考】
天台智者大師的《六妙法門》詳細闡述了數息、隨息、止、觀、還、淨六種禪修方法，是初學禪修者的重要指南。
本經可在CBETA閱讀全文：https://cbetaonline.dila.edu.tw/zh/T1917"""
            
            # 儲存回應到對話歷史
            await user_manager.store_message(user_id, "assistant", "已為您提供禪修引導")
            
            # 發送回覆
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text=meditation_guide,
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        except Exception as e:
            logger.error(f"提供禪修引導時出錯: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text="很抱歉，提供禪修引導時發生錯誤，請稍後再試。",
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        return
    
    # 檢查用戶是否可以發送新問題 (是否正在等待回答)
    status = await user_manager.get_user_status(user_id)
    if status == 'processing' and not user_message in ["主選單", "佛法學習", "生活應用", "心靈成長", "時事省思", "禪修引導", "使用方式"]:
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text="您的上一個問題正在處理中，請等待回答後再提問。如需重新開始，請輸入「清除對話記錄」。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        return
    
    # 檢查請求頻率限制
    if not await user_manager.check_rate_limit(user_id):
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text="您的訊息發送過於頻繁，請稍後再試。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        return
    
    # 過濾敏感內容
    has_sensitive, filtered_message = user_manager.filter_sensitive_content(user_message)
    if has_sensitive:
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text="您的訊息包含不適當內容，已被過濾。我們鼓勵健康、正面的交流。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        return
    
    # 存儲用戶訊息到對話歷史
    await user_manager.store_message(user_id, "user", user_message)
    
    # 檢查是否為簡單問候或自我介紹等問題
    is_simple, simple_type, quick_response = quick_reply_manager.is_simple_query(user_message)
    if is_simple:
        logger.info(f"檢測到簡單問題: {simple_type}")
        # 儲存回應到對話歷史
        await user_manager.store_message(user_id, "bot", quick_response)
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text=quick_response,
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        return
    
    # 處理推薦經典命令
    if user_message.lower().startswith("推薦經典") or user_message == "經典推薦":
        try:
            # 設置用戶狀態為處理中
            await user_manager.set_user_status(user_id, "processing")
            
            # 獲取經典推薦
            recommendations = []
            try:
                if sutra_recommender:
                    # 使用空字符串作為查詢，這樣會基於默認經典進行推薦
                    recommendations = await sutra_recommender.recommend_related_sutras("佛教經典入門推薦")
                    logging.info(f"Generated {len(recommendations)} default sutra recommendations")
            except Exception as e:
                logging.error(f"Error generating default recommendations: {e}", exc_info=True)
            
            line_response = []
            
            # 添加主要回應文本
            intro_text = "以下是一些值得閱讀的經典，適合不同程度的佛法修行者："
            line_response.append(TextSendMessage(text=intro_text))
            
            # 添加經典推薦卡片
            if recommendations and len(recommendations) > 0:
                recommendation_card = create_recommendation_card(recommendations)
                if recommendation_card:
                    line_response.append(recommendation_card)
            else:
                # 如果沒有推薦結果，提供一個默認信息
                line_response.append(TextSendMessage(text="目前無法獲取經典推薦，請稍後再試。"))
            
            # 確保所有消息都有快速回覆按鈕
            response_messages = ensure_quick_replies(line_response)
            
            # 發送回覆
            line_bot_api.reply_message(event.reply_token, response_messages)
            
        except Exception as e:
            logger.error(f"處理推薦經典命令時出錯: {e}", exc_info=True)
            line_bot_api.reply_message(
                event.reply_token,
                ensure_quick_replies([
                    TextSendMessage(
                        text="很抱歉，獲取經典推薦時發生錯誤，請稍後再試。",
                        quick_reply=quick_reply_manager.get_main_menu()
                    )
                ])
            )
        finally:
            # 重置用戶狀態為閒置
            await user_manager.set_user_status(user_id, "idle")
        return
    
    # 傳送「收到訊息」的提示
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text="訊息已收到，正在思考中...")
    )
    
    # 生成回應
    try:
        # 設置用戶狀態為處理中
        await user_manager.set_user_status(user_id, "processing")
        
        # 生成回應
        response_messages = await generate_response(user_message, event, ensure_quick_reply=True)
        
        # 存儲機器人回應到對話歷史 (只存儲第一條文本訊息)
        if response_messages and len(response_messages) > 0 and isinstance(response_messages[0], TextSendMessage):
            await user_manager.store_message(user_id, "assistant", response_messages[0].text)
        
        # 確保所有消息都有快速回覆按鈕
        response_messages = ensure_quick_replies(response_messages)
        
        # 發送回覆
        line_bot_api.reply_message(event.reply_token, response_messages)
        
    except Exception as e:
        logger.error(f"生成回應時出錯: {e}", exc_info=True)
        # 發送錯誤回覆
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text="很抱歉，處理您的問題時發生錯誤，請稍後再試。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
    finally:
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")

# 註冊LINE事件處理器
@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    """LINE訊息事件處理器"""
    asyncio.create_task(handle_text_message(event))
    return 'OK'

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

@router.post("/line-webhook")
async def callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    LINE Webhook 處理器 (替代版本)
    接收來自LINE平台的事件通知，並直接處理
    """
    # 獲取請求頭部的簽名
    signature = request.headers.get('X-Line-Signature', '')
    
    # 獲取請求體
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # 驗證簽名
    try:
        # 解析事件
        events = parser.parse(body_str, signature)
        
        # 處理每個事件
        for event in events:
            # 線上處理部分（只處理文字訊息）
            if event.type == "message" and event.message.type == "text":
                user_id = event.source.user_id
                user_message = event.message.text
                reply_token = event.reply_token

                # 創建或獲取用戶
                user_info = await line_bot_api.get_profile(user_id)
                db_user = get_user_by_line_id(db, user_id)
                if db_user is None:
                    db_user = create_user(db, user_id, user_info.display_name)
                    # 發送歡迎訊息
                    welcome_text = """歡迎使用「菩薩小老師」！
                    
我能幫助您了解佛法、解答修行問題。您可以：
1️⃣ 直接提問佛法問題
2️⃣ 選擇下方選單功能

願您在佛法的道路上找到智慧與平靜 🙏"""
                    await line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=welcome_text)
                    )
                    continue

                # 記錄用戶訊息
                create_message(db, db_user.id, "user", user_message)

                # 處理主選單指令
                if user_message == "主選單" or user_message == "選單" or user_message == "menu":
                    menu_text = """您好，我是『菩薩小老師』😊

請問您想了解什麼？
- 佛法問題：直接輸入您的問題
- 查詢經典：輸入"查經典 關鍵詞"
- 推薦經典：輸入"推薦經典"
- 歷史對話：輸入"歷史對話"
- 清除對話：輸入"清除對話"
                    """
                    await line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=menu_text)
                    )
                    continue
                
                # 處理一般佛法問答
                background_tasks.add_task(
                    process_user_query,
                    db,
                    db_user,
                    user_message,
                    reply_token
                )
                
                # 直接回覆處理中訊息
                processing_text = "菩薩小老師依據佛教教法綜合回答中，請稍候..."
                await line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=processing_text)
                )
            
        return {"status": "success"}
        
    except InvalidSignatureError:
        logger.error("無效的簽名")
        raise HTTPException(status_code=400, detail="無效的簽名")
    except Exception as e:
        logger.error(f"處理LINE Webhook時出錯: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"處理LINE Webhook時出錯: {str(e)}")

async def generate_response(text, event=None, ensure_quick_reply=False):
    """根據用戶輸入生成回覆"""
    try:
        # 生成回應
        response = await response_generator.generate_response(text)
        logging.info(f"Generated response: {response}")

        # 檢查回應中提到的經文ID
        mentioned_sutra_id = None
        references = response.get("references", [])
        
        # 從引用列表中尋找相關性最高的經文ID
        if references:
            # 按相關性排序
            sorted_refs = sorted(references, key=lambda x: x.get("relevance", 0), reverse=True)
            # 獲取相關性最高的經文ID
            if sorted_refs[0].get("relevance", 0) > 0.7 and not sorted_refs[0].get("custom", False):
                mentioned_sutra_id = sorted_refs[0].get("sutra_id")

        # 獲取經典推薦
        recommendations = []
        try:
            if sutra_recommender:
                recommendations = await sutra_recommender.recommend_related_sutras(text, mentioned_sutra_id)
                logging.info(f"Generated {len(recommendations)} sutra recommendations")
        except Exception as e:
            logging.error(f"Error generating recommendations: {e}", exc_info=True)

        # 構建LINE回應
        line_response = []

        # 添加主要回應文本
        line_response.append(TextSendMessage(text=response['text']))

        # 創建經文引用卡片
        if references:
            references_card = FlexSendMessage(
                alt_text="相關經文",
                contents=format_references(references)
            )
            line_response.append(references_card)

        # 添加經典推薦（如果有）
        if recommendations and len(recommendations) > 0:
            recommendation_card = create_recommendation_card(recommendations)
            if recommendation_card:
                line_response.append(recommendation_card)

        # 添加快速回覆按鈕（如果需要）
        if ensure_quick_reply:
            # 確保有至少一個訊息
            if not line_response:
                line_response.append(TextSendMessage(text="請問有什麼佛法問題想了解呢？"))
            
            # 在最後一個訊息添加快速回覆
            last_message = line_response[-1]
            if isinstance(last_message, TextSendMessage) and not hasattr(last_message, 'quick_reply'):
                line_response[-1] = TextSendMessage(
                    text=last_message.text,
                    quick_reply=quick_reply_manager.get_main_menu()
                )

        return line_response
        
    except Exception as e:
        logger.error(f"生成回應時出錯: {e}", exc_info=True)
        return [TextSendMessage(text="很抱歉，我在處理您的請求時遇到了問題。請稍後再試。")]

def create_recommendation_card(recommendations):
    """創建經典推薦卡片"""
    try:
        if not recommendations:
            return None
            
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "相關經典推薦",
                        "weight": "bold",
                        "size": "md",
                        "color": "#876c5a"
                    }
                ],
                "backgroundColor": "#f8f4e6",
                "paddingAll": "10px"  # 減少標題區域的padding
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [],
                "backgroundColor": "#f8f4e6"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "CBETA佛典線上閱讀系統",
                            "uri": "https://cbetaonline.dila.edu.tw/"
                        },
                        "style": "primary",
                        "color": "#c9a063",
                        "height": "sm"
                    }
                ],
                "backgroundColor": "#f8f4e6",
                "paddingAll": "10px"
            }
        }
        
        # 獲取經典分類信息，用於更好的分組顯示
        categories = {}
        try:
            from app.services.sutra_recommender import sutra_recommender
            categories = getattr(sutra_recommender, 'sutra_categories', {})
        except Exception as e:
            logging.error(f"獲取經典分類信息失敗: {e}")
        
        # 經典的關鍵法門和核心關鍵字
        sutra_keywords = {
            "T0235": {"keywords": "空性、無相、般若智慧", "core": "通達空性"},
            "T0251": {"keywords": "五蘊皆空、色即是空", "core": "般若見性"},
            "T0366": {"keywords": "淨土、極樂世界、往生", "core": "信願持名"},
            "T0360": {"keywords": "阿彌陀佛、四十八願", "core": "發願往生"},
            "T0262": {"keywords": "一乘法、法華三昧", "core": "方便善巧"},
            "T0945": {"keywords": "首楞嚴定、如來藏", "core": "觀照真心"},
            "T0293": {"keywords": "十大願王、迴向", "core": "菩薩大願"},
            "T0412": {"keywords": "地藏王、孝道", "core": "救度眾生"},
            "T0449": {"keywords": "藥師如來、十二大願", "core": "消災延壽"},
            "T2008": {"keywords": "禪宗、明心見性", "core": "頓悟法門"},
            "T1911": {"keywords": "止觀、天台宗", "core": "圓融三諦"},
            "T0220": {"keywords": "般若波羅蜜、究竟空", "core": "通達實相"},
            "T1585": {"keywords": "八識、種子、唯識", "core": "轉識成智"},
            "T1579": {"keywords": "五位百法、唯識觀", "core": "瑜伽止觀"},
            "T1586": {"keywords": "三自性、三無性", "core": "唯識無境"},
            "T1564": {"keywords": "中觀、八不中道", "core": "緣起性空"},
            "T1568": {"keywords": "十二門、緣起", "core": "破執顯空"},
            "T2005": {"keywords": "禪機、公案", "core": "參話頭"},
            "X1001": {"keywords": "公案、機鋒", "core": "禪宗開悟"},
            "T1428": {"keywords": "戒律、清淨", "core": "持戒修身"},
            "T1484": {"keywords": "菩薩戒、十重四十八輕", "core": "戒行圓滿"},
            "T1956": {"keywords": "止觀、六妙門", "core": "修習禪定"}
        }
        
        # 嘗試為每個推薦經典找到其類別
        for rec in recommendations[:3]:  # 最多顯示3個推薦
            sutra_id = rec.get("id", "")
            
            # 獲取經典的關鍵詞和核心法門
            keywords = "經典要義"
            core_teaching = "修行法門"
            if sutra_id in sutra_keywords:
                keywords = sutra_keywords[sutra_id]["keywords"]
                core_teaching = sutra_keywords[sutra_id]["core"]
            
            # 創建推薦內容
            content = {
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"《{rec['name']}》",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#594c44",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"核心：{core_teaching}　關鍵詞：{keywords}",
                        "size": "xs",
                        "color": "#8c8c8c",
                        "wrap": True
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"CBETA ID: {sutra_id}",
                                "size": "xs",
                                "color": "#aaaaaa",
                                "flex": 1
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "點此閱讀",
                                    "uri": rec["cbeta_url"]
                                },
                                "style": "primary",
                                "color": "#c9a063",
                                "height": "sm",
                                "flex": 1
                            }
                        ],
                        "margin": "sm"
                    }
                ]
            }
            
            bubble["body"]["contents"].append(content)
            
            # 添加分隔線（除了最後一個項目）
            if recommendations.index(rec) < len(recommendations[:3]) - 1:
                bubble["body"]["contents"].append({
                    "type": "separator",
                    "margin": "md",
                    "color": "#f0e6d2"
                })
        
        return FlexSendMessage(
            alt_text="經典推薦",
            contents=bubble
        )
        
    except Exception as e:
        logger.error(f"創建經典推薦卡片時出錯: {e}", exc_info=True)
        return None 