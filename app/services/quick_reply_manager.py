from linebot.models import QuickReply, QuickReplyButton, MessageAction, URIAction
from typing import Dict, List, Tuple, Any
import logging
import asyncio
import markdown
import emoji
from markdown_it import MarkdownIt
import re
import random

from app.core.config import settings
from app.services.user_manager import user_manager

logger = logging.getLogger(__name__)

class QuickReplyManager:
    def __init__(self):
        # 定義常用的快速回覆類別及其建議問題
        self.quick_reply_categories = {
            "佛法學習": {
                "label": "佛法學習",
                "text": "佛法學習",
                "suggestions": [
                    ("經典詮釋", "什麼是四聖諦？"),
                    ("佛學概念", "如何理解緣起法？"),
                    ("修行方法", "請解釋八正道")
                ]
            },
            "生活應用": {
                "label": "生活應用",
                "text": "生活應用",
                "suggestions": [
                    "如何在日常生活中實踐佛法？",
                    "佛法如何幫助處理壓力？",
                    "如何培養正念？",
                    "佛教徒如何看待財富？",
                    "如何在工作中保持正念？"
                ]
            },
            "心靈成長": {
                "label": "心靈成長",
                "text": "心靈成長",
                "suggestions": [
                    "如何培養慈悲心？",
                    "如何克服嗔恨？",
                    "如何面對人生挫折？",
                    "如何放下執著？",
                    "如何面對生死？"
                ]
            },
            "時事省思": {
                "label": "時事省思",
                "text": "時事省思",
                "suggestions": [
                    "從佛法角度如何看待現代社會過度依賴數位設備的現象？",
                    "佛教觀點下，如何理解和回應全球氣候變化帶來的挑戰？",
                    "如何以佛法智慧面對現代社會的快節奏生活與壓力？",
                    "佛教對於社交媒體時代人際關係變化有何啟示？",
                    "面對經濟不平等日益擴大的社會現象，佛法有何見解？"
                ]
            },
            "禪修引導": {
                "label": "禪修引導",
                "text": "禪修引導",
                "suggestions": [
                    "禪修的基本方法？",
                    "如何進行慈心禪？",
                    "觀呼吸的方法？",
                    "行禪指導？",
                    "如何克服禪修障礙？"
                ]
            },
            "系統功能": {
                "label": "系統功能",
                "text": "系統功能",
                "suggestions": [
                    "清除對話記錄",
                    "提供回饋"
                ]
            },
            "使用方式": {
                "label": "使用方式",
                "text": "使用方式",
                "suggestions": [
                    "如何正確使用菩薩小老師？",
                    "有什麼功能可以使用？",
                    "可以問哪些類型的問題？",
                    "有使用限制嗎？",
                    "如何獲得最佳回答？"
                ]
            }
        }
        
        # 快速回應詞庫 - 處理簡單問候和常見問題
        self.quick_responses = {
            "問候": {
                "keywords": ["你好", "哈囉", "嗨", "早安", "午安", "晚安", "安", "喂"],
                "responses": [
                    "您好！很高興能與您交流。有什麼佛法相關的問題想請教嗎？",
                    "阿彌陀佛！願您今日安康喜樂。有什麼我能為您解答的嗎？",
                    "您好！願您身心自在。有什麼修行或佛法方面的疑惑嗎？"
                ]
            },
            "自我介紹": {
                "keywords": ["你是誰", "你叫什麼", "介紹自己", "自我介紹", "是誰", "機器人", "介紹一下"],
                "responses": [
                    "我是「菩薩小老師」，一位以佛法智慧為基礎的數位助手。我的目標是幫助您理解佛教教義並將其應用於日常生活中。雖然我不能替代師長，但我很樂意在您的學習旅程中提供支持。",
                    "阿彌陀佛！我是「菩薩小老師」，致力於以慈悲和智慧分享佛法。我可以回答佛教相關問題，提供修行建議，或者探討如何將佛法運用在生活中。有什麼我能為您效勞的嗎？",
                    "您好！我是「菩薩小老師」，一個以佛教智慧為基礎的AI助手。我的設計目的是分享佛法知識、提供修行建議，並幫助將佛教智慧融入現代生活。請問有什麼我能協助您的嗎？"
                ]
            },
            "感謝": {
                "keywords": ["謝謝", "感謝", "多謝", "感恩"],
                "responses": [
                    "不客氣！能夠分享佛法智慧是我的榮幸。若有其他問題，隨時請教。",
                    "阿彌陀佛！助人學習是菩薩道的實踐。祝您修行順利！",
                    "隨喜功德！願我們共同在佛法中獲得智慧與安樂。"
                ]
            },
            "讚美": {
                "keywords": ["很棒", "做得好", "厲害", "真好", "不錯", "棒"],
                "responses": [
                    "感恩您的鼓勵！願佛法的光明照亮我們的道路。",
                    "阿彌陀佛！能夠幫到您是我的榮幸。願您在佛法的道路上不斷精進。",
                    "隨喜功德！願我們在法路上共同成長，互相鼓勵。"
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
            items = []
            for category, data in self.quick_reply_categories.items():
                if category != "系統功能":  # 系統功能不顯示在主選單
                    button = QuickReplyButton(
                        action=MessageAction(label=data["label"], text=data["text"])
                    )
                    items.append(button)
            
            return QuickReply(items=items)
            
        except Exception as e:
            logger.error(f"獲取快捷回覆時發生錯誤: {str(e)}")
            return QuickReply(items=[])
    
    def get_suggested_replies(self, query: str, user_id: str = None) -> QuickReply:
        """根據用戶輸入生成建議回覆"""
        try:
            suggestions = []
            
            # 檢查是否包含特定關鍵字
            category = self._get_category_by_keywords(query)
            if category in self.quick_reply_categories:
                suggestions_data = self.quick_reply_categories[category]["suggestions"]
                if isinstance(suggestions_data[0], tuple):
                    suggestions = [text for _, text in suggestions_data]
                else:
                    suggestions = suggestions_data
            
            # 如果沒有找到相關建議，添加默認建議
            if not suggestions:
                suggestions.extend(self.default_suggestions)
            
            # 確保不超過5個建議
            suggestions = suggestions[:5]
            
            # 創建快速回覆按鈕
            items = []
            for suggestion in suggestions:
                items.append(QuickReplyButton(
                    action=MessageAction(
                        label=suggestion[:12] + "..." if len(suggestion) > 12 else suggestion,
                        text=suggestion
                    )
                ))
            
            # 添加主選單按鈕，確保用戶始終能夠返回主選單
            items.append(QuickReplyButton(
                action=MessageAction(
                    label="主選單",
                    text="主選單"
                )
            ))
            
            return QuickReply(items=items)
            
        except Exception as e:
            logger.error(f"生成建議回覆時發生錯誤: {str(e)}")
            items = []
            for suggestion in self.default_suggestions[:2]:
                items.append(QuickReplyButton(
                    action=MessageAction(
                        label=suggestion[:12] + "..." if len(suggestion) > 12 else suggestion,
                        text=suggestion
                    )
                ))
            
            # 在發生錯誤時也確保有主選單按鈕
            items.append(QuickReplyButton(
                action=MessageAction(
                    label="主選單",
                    text="主選單"
                )
            ))
            
            return QuickReply(items=items)
    
    def is_simple_query(self, query: str) -> Tuple[bool, str, str]:
        """
        檢查是否為簡單問候或自我介紹等問題
        
        Args:
            query: 用戶查詢
            
        Returns:
            Tuple[bool, str, str]: (是否為簡單問題, 類型, 回應)
        """
        query = query.lower().strip()
        
        for type_name, data in self.quick_responses.items():
            for keyword in data["keywords"]:
                if keyword in query:
                    # 隨機選擇一個回應
                    response = random.choice(data["responses"])
                    return True, type_name, response
        
        return False, "", ""
    
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
            items = []
            
            # 根據內容關鍵詞檢測類別
            category = self._get_category_by_keywords(content)
            
            # 從該類別中獲取建議
            if category in self.quick_reply_categories:
                suggestions_data = self.quick_reply_categories[category]["suggestions"]
                
                # 處理不同格式的建議數據
                if isinstance(suggestions_data, list):
                    # 如果是元組列表(類別, 文本)
                    if suggestions_data and isinstance(suggestions_data[0], tuple):
                        for label, text in suggestions_data[:3]:  # 只取前3個
                            items.append(QuickReplyButton(
                                action=MessageAction(
                                    label=label[:12] + "..." if len(label) > 12 else label,
                                    text=text
                                )
                            ))
                    # 如果是普通文本列表
                    else:
                        for suggestion in suggestions_data[:3]:  # 只取前3個
                            items.append(QuickReplyButton(
                                action=MessageAction(
                                    label=suggestion[:12] + "..." if len(suggestion) > 12 else suggestion,
                                    text=suggestion
                                )
                            ))
            
            # 添加主選單按鈕
            items.append(QuickReplyButton(
                action=MessageAction(
                    label="主選單",
                    text="主選單"
                )
            ))
            
            # 添加相關類別按鈕
            items.append(QuickReplyButton(
                action=MessageAction(
                    label=self.quick_reply_categories[category]["label"],
                    text=self.quick_reply_categories[category]["text"]
                )
            ))
            
            return QuickReply(items=items)
        except Exception as e:
            logger.error(f"生成上下文快速回覆時發生錯誤: {str(e)}")
            # 如果出錯，返回主選單
            return self.get_main_menu()
    
    def get_category_quick_reply(self, category: str) -> QuickReply:
        """
        獲取特定類別的快速回覆按鈕
        
        Args:
            category (str): 類別名稱
            
        Returns:
            QuickReply: LINE 快速回覆對象
        """
        try:
            items = []
            
            # 根據類別獲取對應的建議
            if category == "系統":
                items.append(QuickReplyButton(
                    action=MessageAction(
                        label="清除對話記錄",
                        text="清除對話記錄"
                    )
                ))
                items.append(QuickReplyButton(
                    action=MessageAction(
                        label="使用方式",
                        text="使用方式"
                    )
                ))
                items.append(QuickReplyButton(
                    action=URIAction(
                        label="提供回饋",
                        uri=self.feedback_form_url
                    )
                ))
            elif category in self.quick_reply_categories:
                suggestions_data = self.quick_reply_categories[category]["suggestions"]
                
                if isinstance(suggestions_data[0], tuple):
                    for label, text in suggestions_data:
                        items.append(QuickReplyButton(
                            action=MessageAction(
                                label=label[:12] + "..." if len(label) > 12 else label,
                                text=text
                            )
                        ))
                else:
                    for suggestion in suggestions_data[:5]:  # 限制最多5個建議
                        items.append(QuickReplyButton(
                            action=MessageAction(
                                label=suggestion[:12] + "..." if len(suggestion) > 12 else suggestion,
                                text=suggestion
                            )
                        ))
            
            # 始終添加一個返回主選單的按鈕
            items.append(QuickReplyButton(
                action=MessageAction(
                    label="回到主選單",
                    text="主選單"
                )
            ))
            
            return QuickReply(items=items)
        except Exception as e:
            logger.error(f"獲取類別快速回覆時發生錯誤: {str(e)}")
            # 出錯時返回主選單
            return self.get_main_menu()
    
    def get_main_menu(self) -> QuickReply:
        """
        獲取主選單
        
        Returns:
            QuickReply: LINE 快速回覆對象
        """
        # 每次重新生成快速回覆項目，避免緩存問題
        items = []
        
        # 添加所有類別按鈕
        for category, info in self.quick_reply_categories.items():
            if category not in ["系統功能"]:  # 排除系統功能
                label = info["label"]
                emoji_prefix = ""
                
                # 為不同類別添加對應的符號
                if category == "佛法學習":
                    emoji_prefix = "📚 "
                elif category == "生活應用":
                    emoji_prefix = "🌱 "
                elif category == "心靈成長":
                    emoji_prefix = "🧘 "
                elif category == "時事省思":
                    emoji_prefix = "🌐 "
                    # 確保文本是"時事省思"，以便line_webhook.py可以識別
                    info["text"] = "時事省思"
                elif category == "禪修引導":
                    emoji_prefix = "🧘‍♀️ "
                elif category == "使用方式":
                    emoji_prefix = "📋 "
                
                # 確保標籤和文本都正確設置
                button = QuickReplyButton(
                    action=MessageAction(
                        label=emoji_prefix + label,
                        text=info["text"]
                    )
                )
                items.append(button)
        
        # 添加清除記錄按鈕
        items.append(QuickReplyButton(
            action=MessageAction(
                label="🗑️ 清除記錄", 
                text="清除對話記錄"
            )
        ))
        
        # 添加回饋按鈕
        items.append(QuickReplyButton(
            action=URIAction(
                label="📝 提供回饋", 
                uri=self.feedback_form_url
            )
        ))
        
        # 確保一定會返回有效的快速回覆對象
        try:
            return QuickReply(items=items)
        except Exception as e:
            logger.error(f"創建快速回覆時發生錯誤: {str(e)}")
            # 如果出錯，返回一個簡單的快速回覆對象
            return QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="主選單", text="主選單"))
            ])
    
    def handle_feedback_request(self) -> str:
        """處理用戶回饋請求"""
        try:
            return f"感謝您的使用！您可以通過以下連結提供寶貴意見：\n{self.feedback_form_url}"
        except Exception as e:
            logger.error(f"處理用戶回饋請求時發生錯誤: {str(e)}")
            return "無法獲取回饋表單連結，請稍後再試。"
    
    def format_markdown(self, text):
        """將Markdown格式的文本轉換為適合在LINE顯示的格式，保持簡潔乾淨"""
        try:
            if not text:
                return ""
            
            # 移除【開示】標籤，但保留內容
            text = re.sub(r'【開示】\s*', '', text)
            
            # 處理列表 - 簡單轉換不添加表情符號
            text = re.sub(r'^\* ', '• ', text, flags=re.MULTILINE)
            text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)
            text = re.sub(r'^(\d+)\. ', r'\1. ', text, flags=re.MULTILINE)  # 保持數字列表簡潔
            
            # 處理標題 - 不添加表情符號
            text = re.sub(r'^# (.*?)$', r'【\1】', text, flags=re.MULTILINE)
            text = re.sub(r'^## (.*?)$', r'【\1】', text, flags=re.MULTILINE)
            text = re.sub(r'^### (.*?)$', r'【\1】', text, flags=re.MULTILINE)
            
            # 處理加粗和斜體 - 使用簡單的符號取代
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 移除加粗標記
            text = re.sub(r'\*(.*?)\*', r'\1', text)      # 移除斜體標記
            text = re.sub(r'_(.*?)_', r'\1', text)        # 移除底線標記
            
            # 處理引用 - 簡化引用格式
            text = re.sub(r'^> (.*?)$', r'"\1"', text, flags=re.MULTILINE)
            
            # 添加適當的空行以提高可讀性
            text = re.sub(r'\n\n', '\n\n', text)
            
            # 移除多餘的空行
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            # 只保留少量必要的關鍵詞替換，不使用表情符號
            simple_keywords = {
                "第一步": "第一步",
                "第二步": "第二步",
                "第三步": "第三步",
                "第四步": "第四步",
                "第五步": "第五步",
                "解說": "解說",
                "實踐": "實踐"
            }
            
            for keyword, replacement in simple_keywords.items():
                text = re.sub(fr'\b{keyword}\b', replacement, text)
            
            return text
        except Exception as e:
            logger.error(f"Markdown格式化發生錯誤: {e}")
            return text
            
    def handle_usage_guide(self) -> str:
        """
        處理使用方式請求
        
        Returns:
            str: 使用方式指南文本
        """
        usage_guide = """
# 菩薩小老師使用指南

## 如何使用
1. 直接輸入問題即可獲得回應
2. 點擊底部快速按鈕選擇主題
3. 清除記錄可重置對話歷史

## 功能分類
- 佛法學習：教理講解與經典解析
- 生活應用：佛法在日常生活的運用
- 心靈成長：情緒管理與煩惱轉化
- 時事省思：佛法視角看待現代議題
- 禪修引導：正念練習與冥想指導

## 使用建議
1. 一次提問一個問題效果最佳
2. 表述清晰具體能獲得更好回應
3. 重要問題請諮詢專業法師

如有使用問題或建議，請點選「提供回饋」按鈕。
"""
        return self.format_markdown(usage_guide)

# 單例模式實例
quick_reply_manager = QuickReplyManager() 