import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
from datetime import datetime

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
            # 確保使用有效的URL
            url = f"https://cbetaonline.dila.edu.tw/zh/{sutra_id}" if sutra_id else "https://cbetaonline.dila.edu.tw/"
            
            # 提取文本內容，顯示經文片段
            text_content = ref.get("text", "")
            content_to_show = text_content[:150] + "..." if len(text_content) > 150 else text_content
            
            # 移除sutra_name中可能的書名號，避免重複
            clean_sutra_name = sutra_name.replace('《', '').replace('》', '')
            
            body_contents = [
                {
                    "type": "text",
                    "text": f"{content_to_show}",
                    "size": settings.FONT_SIZE_SMALL,
                    "wrap": True,
                    "color": "#555555"
                },
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#f5f5f5"
                },
                {
                    "type": "text",
                    "text": f"CBETA: {sutra_id}",
                    "size": "xs",
                    "color": "#aaaaaa",
                    "margin": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "查看完整經文",
                        "uri": url
                    },
                    "style": "link",
                    "margin": "sm",
                    "height": "sm"
                }
            ]
            
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
                    "contents": body_contents,
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
                        "color": "#888888"
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
    
    # 檢查用戶是否可以發送新問題 (是否正在等待回答)
    status = await user_manager.get_user_status(user_id)
    if status == 'processing' and not user_message in ["主選單", "佛法學習", "生活應用", "心靈成長", "時事省思", "禪修引導"]:
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
    
    # 傳送「收到訊息」的提示
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text="訊息已收到，正在思考中...")
    )
    
    # 設置用戶狀態為處理中
    await user_manager.set_user_status(user_id, "processing")
    
    # 主選單處理
    if user_message == "主選單":
        welcome_text = """您好，我是『菩薩小老師』😊

我專注於佛教教育與修行指導，能根據您的修行階段提供相應引導。請隨時提問佛法相關問題，我將以慈悲、智慧與耐心回應您的疑惑。

若有涉及密法或特殊教法的問題，建議您尋求正法道場、合格法師或佛教中心的指導。

請選擇以下主題或直接提問："""
        
        line_bot_api.reply_message(
            event.reply_token,
            ensure_quick_replies([
                TextSendMessage(
                    text=welcome_text,
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ])
        )
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        return
    
    # 處理各功能直接請求
    if user_message in ["佛法學習", "生活應用", "心靈成長"]:
        category = user_message
        
        # 設定不同類別的預設問題
        category_questions = {
            "佛法學習": "請簡要介紹佛教的基本教義和修行方法，包括四聖諦、八正道和緣起法",
            "生活應用": "請說明如何將佛法智慧應用於日常生活中面對壓力、人際關係和工作挑戰",
            "心靈成長": "請解釋佛法如何幫助我們處理負面情緒、培養慈悲心和開發內在智慧"
        }
        
        try:
            # 使用預設問題生成完整回應
            default_question = category_questions.get(category)
            response_data = await response_generator.generate_response(default_question, user_id)
            response_text = response_data["text"]
            references = response_data["references"]
            
            # 存儲機器人回應到對話歷史
            await user_manager.store_message(user_id, "assistant", response_text)
            
            # 應用Markdown格式化，保持簡潔
            formatted_response = quick_reply_manager.format_markdown(response_text)
            
            # 美化回應文本中的分隔線，使用簡單的分隔線
            formatted_response = formatted_response.replace("\n---\n", "\n" + "----------" + "\n")
            
            # 從用戶輸入自動檢測內容類別
            category = quick_reply_manager._get_category_by_keywords(user_message)
            
            # 移除標題添加的部分，直接使用格式化後的回應
            # formatted_response = f"【{category}】\n\n" + formatted_response
            
            # 移除多餘的視覺標記和表情符號
            # 回覆主要訊息
            messages_to_reply = [
                # 主要回應文本
                TextSendMessage(text=formatted_response, quick_reply=quick_reply_manager.get_main_menu())
            ]
            
            # 始終顯示引用經文的Flex Message，即使沒有引用也顯示提示
            flex_message = FlexSendMessage(
                alt_text="相關經文",
                contents=format_references(references)
            )
            # 確保添加快速回覆按鈕
            flex_message.quick_reply = quick_reply_manager.get_main_menu()
            messages_to_reply.append(flex_message)
            
            # 確保所有消息都有快速回覆按鈕
            for msg in messages_to_reply:
                if not hasattr(msg, 'quick_reply') or not msg.quick_reply:
                    msg.quick_reply = quick_reply_manager.get_main_menu()
            
            # 發送回覆
            line_bot_api.reply_message(event.reply_token, messages_to_reply)
            
        except Exception as e:
            logger.error(f"生成{category}回應時出錯: {e}", exc_info=True)
            # 發生錯誤時發送簡單的提示訊息
            intro_text = f"關於「{category}」，您可以隨意發問，我將盡力解答。"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=intro_text,
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            )
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        return
    
    # 時事省思處理
    if user_message == "時事省思":
        try:
            # 獲取新聞數據
            news_list = await news_processor.get_daily_news()
            
            # 創建 Flex Message 內容
            flex_content = {
                "type": "carousel",
                "contents": []
            }
            
            # 為每條新聞創建一個泡泡
            for news in news_list:
                title = news.get("title", "今日觀察")
                content = news.get("content", "")
                perspective = news.get("perspective", "")
                category = news.get("category", "一般新聞")
                source = news.get("source", "")
                
                # 裁剪過長的內容
                if len(content) > 100:
                    content = content[:97] + "..."
                
                # 創建新聞泡泡
                bubble = {
                    "type": "bubble",
                    "size": "mega",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": category,
                                "color": "#FFFFFF",
                                "weight": "bold",
                                "size": "sm"
                            },
                            {
                                "type": "text",
                                "text": title,
                                "color": "#FFFFFF",
                                "weight": "bold",
                                "size": "xl",
                                "wrap": True,
                                "maxLines": 3
                            }
                        ],
                        "backgroundColor": settings.THEME_COLOR,
                        "paddingAll": "12px",
                        "spacing": "sm"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📊 要點",
                                "weight": "bold",
                                "size": "md",
                                "color": "#555555"
                            },
                            {
                                "type": "text",
                                "text": content,
                                "size": "sm",
                                "wrap": True,
                                "color": "#111111",
                                "margin": "md"
                            },
                            {
                                "type": "separator",
                                "margin": "lg"
                            },
                            {
                                "type": "text",
                                "text": "🔍 客觀省思",
                                "weight": "bold",
                                "size": "md",
                                "color": "#555555",
                                "margin": "lg"
                            },
                            {
                                "type": "text",
                                "text": perspective,
                                "size": "sm",
                                "wrap": True,
                                "color": "#111111",
                                "margin": "md"
                            }
                        ],
                        "paddingAll": "15px",
                        "spacing": "sm"
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"來源: {source}",
                                "size": "xs",
                                "color": "#AAAAAA",
                                "align": "end"
                            },
                            {
                                "type": "button",
                                "style": "primary",
                                "action": {
                                    "type": "uri",
                                    "label": "閱讀原文",
                                    "uri": news.get("url", "https://www.google.com/search?q=" + title)
                                },
                                "color": settings.THEME_COLOR,
                                "margin": "md",
                                "height": "sm"
                            }
                        ],
                        "paddingAll": "10px",
                        "spacing": "sm"
                    }
                }
                
                flex_content["contents"].append(bubble)
            
            # 回覆消息
            messages_to_reply = [
                # 標題
                TextSendMessage(
                    text=f"📰 今日國際與政經觀察 - {datetime.now().strftime('%Y/%m/%d')}\n願以智慧之眼觀世界，以平等之心待萬物",
                    quick_reply=quick_reply_manager.get_main_menu()
                ),
                # Flex Message
                FlexSendMessage(
                    alt_text="今日國際與政經觀察",
                    contents=flex_content,
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            ]
            
            # 發送回覆
            line_bot_api.reply_message(event.reply_token, messages_to_reply)
            
            # 重置用戶狀態為閒置
            await user_manager.set_user_status(user_id, "idle")
        except Exception as e:
            logger.error(f"處理時事省思時出錯: {e}", exc_info=True)
            # 發生錯誤時發送一個簡單的錯誤訊息
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="很抱歉，獲取新聞時發生錯誤，請稍後再試。",
                    quick_reply=quick_reply_manager.get_main_menu()
                )
            )
            # 發生錯誤時也重置用戶狀態
            await user_manager.set_user_status(user_id, "idle")
        return
    
    # 禪修引導處理
    if user_message == "禪修引導":
        meditation_text = """ 🧘‍♀️ 禪修引導

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
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=meditation_text,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
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
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        return
    
    # 處理使用方式
    if user_message == "使用方式":
        usage_guide = quick_reply_manager.handle_usage_guide()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=usage_guide,
                quick_reply=quick_reply_manager.get_main_menu()
            )
        )
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        return
    
    # 使用回饋處理
    if user_message == "提供回饋":
        response = quick_reply_manager.handle_feedback_request()
        
        # 添加操作說明按鈕
        buttons = [
            {
                "type": "text",
                "text": "使用方式",
                "color": "#1DB446",
                "weight": "bold",
                "action": {
                    "type": "message",
                    "label": "使用方式",
                    "text": "使用方式"
                }
            }
        ]
        
        # 創建包含按鈕的Flex Message
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": response,
                        "wrap": True,
                        "size": settings.FONT_SIZE_MEDIUM,
                        "color": "#555555"
                    }
                ],
                "paddingAll": "15px"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": buttons,
                "paddingAll": "12px"
            }
        }
        
        # 明確設置 quick_reply
        flex_message = FlexSendMessage(
            alt_text="提供回饋",
            contents=flex_content,
            quick_reply=quick_reply_manager.get_main_menu()
        )
        
        line_bot_api.reply_message(event.reply_token, [flex_message])
        
        # 重置用戶狀態為閒置
        await user_manager.set_user_status(user_id, "idle")
        return
    
    # 生成回應
    response_data = await response_generator.generate_response(user_message, user_id)
    response_text = response_data["text"]
    references = response_data["references"]
    
    # 存儲機器人回應到對話歷史
    await user_manager.store_message(user_id, "assistant", response_text)
    
    # 應用Markdown格式化，保持簡潔
    formatted_response = quick_reply_manager.format_markdown(response_text)
    
    # 美化回應文本，移除多餘的符號和標記
    formatted_response = formatted_response.replace("\n---\n", "\n" + "----------" + "\n")
    formatted_response = formatted_response.replace("【", "")
    formatted_response = formatted_response.replace("】", "")
    formatted_response = formatted_response.replace("*", "")
    
    # 回覆主要訊息
    messages_to_reply = [
        # 主要回應文本
        TextSendMessage(text=formatted_response, quick_reply=quick_reply_manager.get_main_menu())
    ]
    
    # 始終顯示引用經文的Flex Message，即使沒有引用也顯示提示
    flex_message = FlexSendMessage(
        alt_text="相關經文",
        contents=format_references(references)
    )
    # 確保添加快速回覆按鈕
    flex_message.quick_reply = quick_reply_manager.get_main_menu()
    messages_to_reply.append(flex_message)
    
    # 確保所有消息都有快速回覆按鈕
    for msg in messages_to_reply:
        if not hasattr(msg, 'quick_reply') or not msg.quick_reply:
            msg.quick_reply = quick_reply_manager.get_main_menu()
    
    # 發送回覆
    line_bot_api.reply_message(event.reply_token, messages_to_reply)
    
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
                processing_text = "菩薩小老師依據佛教教義綜合回答中，請稍候..."
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