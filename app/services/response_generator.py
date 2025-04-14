import logging
from typing import List, Dict, Any, Optional
import json

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.sutra_retriever import sutra_retriever
from app.services.user_manager import user_manager

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResponseGenerator:
    """
    回應生成器類別
    負責根據用戶問題和檢索到的經文生成回應
    """
    
    def __init__(self):
        """初始化回應生成器"""
        # 初始化GPT模型
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.GPT_MODEL,
            temperature=0.3
        )
        
        # 初始化提示模板 - 用於生成回應
        self.response_prompt = ChatPromptTemplate.from_template("""
您是一位精通佛教唯識學的專家，能夠提供有關佛法的詮釋、解說和應用指導。

用戶問題：{user_query}

以下是與問題相關的經文:
{relevant_texts}

回應要求：
1. 根據用戶的認知層級（{response_level}）調整回應深度
2. 使用四攝法策略 - {four_she_strategy} 來建立親近感
3. 保持回應簡潔，易於理解，但不失專業性
4. 提供適合用戶認知層級的解釋和實踐建議
5. 回應應體現唯識學核心概念，幫助用戶理解心識轉化的過程
6. 適度引用提供的經文內容，以增強回應的可信度
7. 你可以使用Markdown語法來格式化回應，使用**粗體**強調重點，使用*斜體*表示經文引用，使用列表或分隔線等元素增強可讀性
8. 回應結構建議：概述 → 核心解釋 → 實踐指導 → 結語

請開始你的回應（保持在500字以內）:
""")
        
        # 初始化提示模板 - 用於分類用戶認知層級
        self.classification_prompt = ChatPromptTemplate.from_template("""
您是一位精通佛教唯識學的專家。您的任務是根據用戶的問題，確定其認知層級和問題類型。

用戶問題：{user_query}

請根據以下說明，分析用戶的認知層級：

### 認知層級
1. 第一層（基礎認知層）：對佛法知識缺乏，或僅有表面了解，思維方式較為世俗，通常關注眼前問題的解決。
2. 第二層（進階探索層）：已初步接觸佛法，了解一些基本概念，開始思考更深層的問題，但尚未系統性學習。
3. 第三層（深度理解層）：已經系統性學習佛法，能理解較深的佛法概念，能主動思考佛法與生活的關係。
4. 第四層（修行實踐層）：已有深厚佛法基礎，關注修行實踐和證悟過程，能從唯識學角度思考問題。

### 問題類型
1. 煩惱型：主要是尋求解決現實問題的答案，如情緒、人際關係等
2. 價值觀衝突型：探討佛法與現代生活的矛盾與整合
3. 虛無傾向型：對人生意義的質疑，或面臨重大生命危機
4. 求法欲望型：主動尋求佛法智慧和修行方法

請以JSON格式分析用戶的認知層級和問題類型：
""")
        
        # 初始化四攝法策略選擇提示模板
        self.four_she_prompt = ChatPromptTemplate.from_template("""
您是一位精通佛教四攝法的專家。根據用戶的認知層級和問題類型，請選擇最適合的四攝法策略。

用戶認知層級：{user_level}
問題類型：{issue_type}

四攝法包括：
1. 布施（Dana）：通過給予幫助建立關係，可以是物質的或精神的給予
2. 愛語（Priyavacana）：用溫和、親切的言語與人交流，增進理解
3. 利行（Arthakrtya）：通過實際行動幫助他人，指導他們走向正確的道路
4. 同事（Samanarthata）：融入他人的處境，以平等態度與人交往

請考慮以下對應關係：
- 第一層認知的用戶通常適合布施和愛語為主的策略
- 第二層認知的用戶適合愛語和利行策略
- 第三層和第四層認知的用戶適合利行和同事策略
- 煩惱型問題適合愛語和利行
- 價值觀衝突型問題適合利行和同事
- 虛無傾向型問題適合布施和愛語
- 求法欲望型問題適合利行和同事

請指定最主要的策略（僅選一個）：
""")
        
    async def classify_user_input(self, user_query: str) -> Dict[str, str]:
        """
        對用戶輸入進行分類，判斷認知層級和問題類型
        
        Args:
            user_query: 用戶問題
            
        Returns:
            Dict: 分類結果，包含認知層級和問題類型
        """
        try:
            # 準備提示
            classification_prompt = self.classification_prompt.format(
                user_query=user_query
            )
            
            # 調用LLM
            classification_response = self.llm.invoke(classification_prompt)
            
            # 從回應中提取JSON
            json_start = classification_response.content.find('{')
            json_end = classification_response.content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = classification_response.content[json_start:json_end]
                classification_result = json.loads(json_str)
                
                # 確保結果包含必要的鍵
                if "level" not in classification_result or "type" not in classification_result:
                    # 嘗試替代鍵名
                    level = classification_result.get("認知層級", classification_result.get("user_level", "第一層"))
                    issue_type = classification_result.get("問題類型", classification_result.get("issue_type", "煩惱型"))
                    
                    classification_result = {
                        "level": level,
                        "type": issue_type
                    }
            else:
                # 無法解析JSON，使用默認值
                classification_result = {
                    "level": "第一層",
                    "type": "煩惱型"
                }
            
            logger.info(f"用戶輸入分類結果: {classification_result}")
            return classification_result
            
        except Exception as e:
            logger.error(f"分類用戶輸入時出錯: {e}", exc_info=True)
            # 返回默認分類
            return {
                "level": "第一層",
                "type": "煩惱型"
            }
    
    async def select_four_she_strategy(self, user_level: str, issue_type: str) -> str:
        """
        根據用戶認知層級和問題類型選擇四攝法策略
        
        Args:
            user_level: 用戶認知層級
            issue_type: 問題類型
            
        Returns:
            str: 選擇的四攝法策略
        """
        try:
            # 準備提示
            strategy_prompt = self.four_she_prompt.format(
                user_level=user_level,
                issue_type=issue_type
            )
            
            # 調用LLM
            strategy_response = self.llm.invoke(strategy_prompt)
            
            # 提取策略名稱
            strategy = strategy_response.content.strip()
            
            # 標準化策略名稱
            if "布施" in strategy:
                return "布施"
            elif "愛語" in strategy:
                return "愛語"
            elif "利行" in strategy:
                return "利行"
            elif "同事" in strategy:
                return "同事"
            else:
                # 根據層級指定默認策略
                if "一層" in user_level:
                    return "布施"
                elif "二層" in user_level:
                    return "愛語"
                elif "三層" in user_level:
                    return "利行"
                else:
                    return "同事"
                
        except Exception as e:
            logger.error(f"選擇四攝法策略時出錯: {e}", exc_info=True)
            # 返回默認策略
            return "愛語"
    
    async def generate_response(self, user_query: str, user_id: str = "anonymous") -> Dict:
        """
        生成對用戶問題的回應
        
        Args:
            user_query: 用戶問題
            user_id: 用戶ID
            
        Returns:
            Dict: 生成的回應，包含回應文本和引用的經文
        """
        try:
            # 1. 分類用戶輸入
            classification = await self.classify_user_input(user_query)
            user_level = classification["level"]
            issue_type = classification["type"]
            
            # 2. 選擇四攝法策略
            four_she_strategy = await self.select_four_she_strategy(user_level, issue_type)
            
            # 3. 查詢相關經文
            relevant_texts = await sutra_retriever.query_sutra(user_query, top_k=3)
            
            # 準備經文文本用於提示
            formatted_texts = []
            for i, text in enumerate(relevant_texts):
                if "custom_document" in text and text["custom_document"]:
                    # 自定義文檔
                    formatted_texts.append(f"{i+1}. 自定義文檔《{text['source']}》:\n{text['text']}")
                else:
                    # CBETA經文
                    formatted_texts.append(f"{i+1}. 經典《{text['sutra']}》(ID: {text['sutra_id']}):\n{text['text']}")
            
            texts_str = "\n\n".join(formatted_texts) if formatted_texts else "未找到相關經文。"
            
            # 獲取對話歷史
            chat_history = await user_manager.get_chat_history(user_id)
            history_context = ""
            
            # 格式化對話歷史
            if chat_history and len(chat_history) > 0:
                # 只使用最近的幾輪對話
                recent_history = chat_history[-settings.HISTORY_LIMIT * 2:]  # 用戶和機器人的消息對
                
                history_pairs = []
                for i in range(0, len(recent_history), 2):
                    if i+1 < len(recent_history):
                        # 完整的一對對話
                        user_msg = recent_history[i]["content"]
                        bot_msg = recent_history[i+1]["content"]
                        history_pairs.append(f"用戶: {user_msg}\n機器人: {bot_msg}")
                
                if history_pairs:
                    history_context = "### 對話歷史:\n" + "\n\n".join(history_pairs)
            
            # 4. 生成回應
            response_prompt = self.response_prompt.format(
                user_query=user_query,
                relevant_texts=texts_str,
                response_level=user_level,
                four_she_strategy=four_she_strategy
            )
            
            # 如果有對話歷史，加到提示中
            if history_context:
                response_prompt = response_prompt + "\n\n" + history_context + "\n\n請考慮上述對話歷史，保持一致性地回應用戶的問題。"
            
            # 調用LLM
            response = self.llm.invoke(response_prompt)
            
            # 5. 整理回應
            references = []
            for text in relevant_texts:
                if "custom_document" in text and text["custom_document"]:
                    # 自定義文檔參考
                    references.append({
                        "text": text["text"],
                        "source": text["source"],
                        "custom": True
                    })
                else:
                    # CBETA經文參考
                    references.append({
                        "text": text["text"],
                        "sutra": text["sutra"],
                        "sutra_id": text["sutra_id"],
                        "custom": False
                    })
            
            logger.info(f"生成回應，用戶層級: {user_level}, 策略: {four_she_strategy}")
            
            return {
                "text": response.content,
                "references": references,
                "user_level": user_level,
                "issue_type": issue_type,
                "four_she_strategy": four_she_strategy
            }
            
        except Exception as e:
            logger.error(f"生成回應時出錯: {e}", exc_info=True)
            # 返回錯誤回應
            return {
                "text": "很抱歉，我在處理您的問題時遇到了困難。請稍後再嘗試，或者換一種方式提問。",
                "references": [],
                "user_level": "未知",
                "issue_type": "未知",
                "four_she_strategy": "未知"
            }

# 單例模式實例
response_generator = ResponseGenerator() 