from linebot.models import QuickReply, QuickReplyButton, MessageAction, URIAction
from typing import Dict, List, Tuple, Any
import logging
import asyncio
import markdown
import emoji
from markdown_it import MarkdownIt

from app.core.config import settings
from app.services.user_manager import user_manager

logger = logging.getLogger(__name__)

class QuickReplyManager:
    def __init__(self):
        # 定義常用的快速回覆類別及其建議問題
        self.quick_replies = {
            "佛法學習": {
                "label": "佛法學習",
                "text": "我想學習佛法",
                "suggestions": [
                    ("經典詮釋", "什麼是四聖諦？"),
                    ("佛學概念", "如何理解緣起法？"),
                    ("修行方法", "請解釋八正道")
                ]
            },
            "生活應用": {
                "label": "生活應用",
                "text": "我想了解佛法在生活中的應用",
                "suggestions": [
                    ("人際關係", "如何用佛法處理人際關係？"),
                    ("工作壓力", "工作壓力大時如何運用佛法？"),
                    ("正念練習", "如何培養正念生活？")
                ]
            },
            "心靈成長": {
                "label": "心靈成長",
                "text": "我想探索心靈成長",
                "suggestions": [
                    ("情緒管理", "如何用佛法智慧處理負面情緒"),
                    ("自我探索", "如何從佛法角度了解自己的本性"),
                    ("轉化煩惱", "如何將煩惱轉化為菩提")
                ]
            },
            "系統": {
                "label": "系統",
                "text": "系統功能",
                "suggestions": [
                    ("清除記錄", "清除對話記錄"),
                    ("使用說明", "查看使用說明"),
                    ("用戶回饋", "提供使用回饋")
                ]
            }
        }
        
        # 定義默認建議，當沒有找到匹配的內容時使用
        self.default_suggestions = [
            "請一次只提出一個問題",
            "您可以參考以下問題格式：",
            "1. 請問[具體問題]？",
            "2. 我想了解[具體主題]",
            "3. 請解釋[具體概念]"
        ]
        
        # 關鍵詞映射表，用於將用戶輸入映射到對應類別
        self.keyword_mapping = {
            "佛法學習": [
                "四聖諦", "八正道", "緣起", "無常", "唯識", "菩提", "佛陀", 
                "經典", "修行", "菩薩", "戒律", "涅槃", "禪定", "般若"
            ],
            "生活應用": [
                "工作", "職場", "家庭", "關係", "朋友", "壓力", "衝突", 
                "溝通", "情緒", "生活", "困難", "決定", "選擇"
            ],
            "心靈成長": [
                "情緒", "憤怒", "焦慮", "恐懼", "煩惱", "苦惱", "痛苦", 
                "困惑", "迷茫", "執著", "放下", "療癒", "成長"
            ],
            "禪修引導": [
                "禪修", "打坐", "冥想", "正念", "觀想", "靜心", "呼吸", 
                "專注", "平靜", "專住", "放鬆"
            ],
            "時事省思": [
                "時事", "新聞", "社會", "世界", "政治", "經濟", "環境", 
                "科技", "全球", "議題", "現象"
            ]
        }
        
        # 用戶回饋表單URL
        self.feedback_form_url = settings.USER_FEEDBACK_FORM
        
        # 初始化Markdown解析器
        self.md = MarkdownIt("commonmark")
        
        logger.info("QuickReplyManager 初始化完成")
    
    def get_quick_replies(self, user_id: str = None) -> List[Dict[str, Any]]:
        """獲取快捷回覆選項"""
        try:
            replies = []
            for category, data in self.quick_replies.items():
                if category != "系統":  # 系統功能不顯示在主選單
                    replies.append({
                        "type": "message",
                        "label": data["label"],
                        "text": data["text"]
                    })
            
            return replies
            
        except Exception as e:
            logger.error(f"獲取快捷回覆時發生錯誤: {str(e)}")
            return []
    
    def get_suggested_replies(self, query: str, user_id: str = None) -> List[Dict[str, Any]]:
        """根據用戶輸入生成建議回覆"""
        try:
            suggestions = []
            
            # 檢查是否包含特定關鍵字
            category = self._get_category_by_keywords(query)
            if category in self.quick_replies:
                suggestions_data = self.quick_replies[category]["suggestions"]
                suggestions = [text for _, text in suggestions_data]
            
            # 如果沒有找到相關建議，添加默認建議
            if not suggestions:
                suggestions.extend(self.default_suggestions)
            
            # 確保不超過5個建議
            suggestions = suggestions[:5]
            
            return [{"type": "message", "text": suggestion} for suggestion in suggestions]
            
        except Exception as e:
            logger.error(f"生成建議回覆時發生錯誤: {str(e)}")
            return [{"type": "message", "text": suggestion} for suggestion in self.default_suggestions]
    
    def handle_clear_history(self, user_id: str) -> str:
        """處理清除對話歷史的請求"""
        try:
            # 使用UserManager清除對話歷史
            success = asyncio.run(user_manager.clear_chat_history(user_id))
            if success:
                return "已清除對話記憶緩存。您可以開始新的對話。"
            else:
                return "清除對話記憶緩存時發生錯誤，請稍後再試。"
        except Exception as e:
            logger.error(f"清除對話歷史時發生錯誤: {str(e)}")
            return "清除對話記憶緩存時發生錯誤，請稍後再試。"

    def _get_category_by_keywords(self, content: str) -> str:
        """根據關鍵詞判斷內容類別"""
        max_matches = 0
        best_category = "生活應用"  # 默認類別
        
        for category, keywords in self.keyword_mapping.items():
            matches = sum(1 for keyword in keywords if keyword in content)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category
    
    def get_context_quick_reply(self, content: str) -> QuickReply:
        """
        根據內容智能推薦相關的快速回覆按鈕
        
        Args:
            content (str): 對話內容
            
        Returns:
            QuickReply: LINE 快速回覆對象
        """
        try:
            # 判斷內容類別
            category = self._get_category_by_keywords(content)
            
            # 獲取該類別的按鈕選項或使用默認類別
            if category not in self.quick_replies:
                category = "佛法學習"  # 如果找不到匹配類別，使用默認類別
            
            buttons = []
            for label, text in self.quick_replies[category]["suggestions"]:
                action = MessageAction(label=label, text=text)
                button = QuickReplyButton(action=action)
                buttons.append(button)
            
            # 加入一個返回主選單的按鈕
            action = MessageAction(label="🏠 主選單", text="主選單")
            button = QuickReplyButton(action=action)
            buttons.append(button)

            # 加入一個回饋表單按鈕
            uri_action = URIAction(label="📝 用戶回饋", uri=self.feedback_form_url)
            feedback_button = QuickReplyButton(action=uri_action)
            buttons.append(feedback_button)
            
            return QuickReply(items=buttons)
            
        except Exception as e:
            logger.error(f"生成快速回覆時發生錯誤: {str(e)}")
            # 返回默認的佛法學習類別
            buttons = []
            for label, text in self.quick_replies["佛法學習"]["suggestions"]:
                action = MessageAction(label=label, text=text)
                button = QuickReplyButton(action=action)
                buttons.append(button)
            return QuickReply(items=buttons)
    
    def get_category_quick_reply(self, category: str) -> QuickReply:
        """
        獲取特定類別的快速回覆按鈕
        
        Args:
            category (str): 類別名稱
            
        Returns:
            QuickReply: LINE 快速回覆對象
        """
        try:
            if category in self.quick_replies:
                buttons = []
                for label, text in self.quick_replies[category]["suggestions"]:
                    action = MessageAction(label=label, text=text)
                    button = QuickReplyButton(action=action)
                    buttons.append(button)
                
                # 加入一個返回主選單的按鈕
                action = MessageAction(label="🏠 主選單", text="主選單")
                button = QuickReplyButton(action=action)
                buttons.append(button)

                # 加入一個回饋表單按鈕
                uri_action = URIAction(label="📝 用戶回饋", uri=self.feedback_form_url)
                feedback_button = QuickReplyButton(action=uri_action)
                buttons.append(feedback_button)
                
                return QuickReply(items=buttons)
            else:
                # 如果類別不存在，返回主選單
                return self.get_main_menu()
        except Exception as e:
            logger.error(f"獲取類別快速回覆時發生錯誤: {str(e)}")
            return self.get_main_menu()
    
    def get_main_menu(self) -> QuickReply:
        """
        獲取主選單快速回覆按鈕
        
        Returns:
            QuickReply: LINE 快速回覆對象
        """
        try:
            buttons = []
            for category, data in self.quick_replies.items():
                if category != "系統":  # 系統功能不顯示在主選單
                    action = MessageAction(label=data["label"], text=data["text"])
                    button = QuickReplyButton(action=action)
                    buttons.append(button)
            
            # 添加特殊功能選項
            action1 = MessageAction(label="📰 時事省思", text="時事省思")
            button1 = QuickReplyButton(action=action1)
            buttons.append(button1)
            
            action2 = MessageAction(label="🧘 禪修引導", text="禪修引導")
            button2 = QuickReplyButton(action=action2)
            buttons.append(button2)
            
            action3 = MessageAction(label="⚙️ 系統功能", text="系統功能")
            button3 = QuickReplyButton(action=action3)
            buttons.append(button3)
            
            # 添加用戶回饋按鈕
            uri_action = URIAction(label="📝 用戶回饋", uri=self.feedback_form_url)
            feedback_button = QuickReplyButton(action=uri_action)
            buttons.append(feedback_button)
            
            return QuickReply(items=buttons)
        except Exception as e:
            logger.error(f"獲取主選單時發生錯誤: {str(e)}")
            # 返回簡化的選單
            buttons = []
            action1 = MessageAction(label="佛法學習", text="我想學習佛法")
            button1 = QuickReplyButton(action=action1)
            buttons.append(button1)
            
            action2 = MessageAction(label="生活應用", text="我想了解佛法在生活中的應用")
            button2 = QuickReplyButton(action=action2)
            buttons.append(button2)
            
            return QuickReply(items=buttons)
    
    def handle_feedback_request(self) -> str:
        """處理用戶回饋請求"""
        try:
            return f"感謝您的使用！您可以通過以下連結提供寶貴意見：\n{self.feedback_form_url}"
        except Exception as e:
            logger.error(f"處理用戶回饋請求時發生錯誤: {str(e)}")
            return "無法獲取回饋表單連結，請稍後再試。"
    
    def format_markdown(self, text: str) -> str:
        """
        將Markdown文本轉換為LINE可接受的格式
        
        Args:
            text: Markdown格式的文本
            
        Returns:
            str: 格式化後的文本
        """
        try:
            # 將Markdown轉換為HTML
            html = self.md.render(text)
            
            # LINE不支持HTML，所以我們需要進行一些基本的文本替換
            # 加粗 **text** -> 【text】
            text = text.replace("**", "【").replace("**", "】")
            
            # 斜體 *text* -> 「text」
            text = text.replace("*", "「").replace("*", "」")
            
            # 列表項 - item -> • item
            text = text.replace("\n- ", "\n• ")
            
            # 添加表情符號支持
            text = emoji.emojize(text, language='alias')
            
            return text
        except Exception as e:
            logger.error(f"格式化Markdown時發生錯誤: {str(e)}")
            return text  # 返回原始文本

# 單例模式實例
quick_reply_manager = QuickReplyManager() 