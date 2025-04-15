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
您是「菩薩小老師」，一位結合唯識學智慧的佛法導師，能以自然又有深度的方式引導學習者。

用戶問題：{user_query}

以下是與問題相關的經文:
{relevant_texts}

回應指南：
1. 根據用戶層級（{response_level}）調整回應深度，採用{four_she_strategy}的溝通方式
2. 以簡潔自然的對話風格回應，同時保持專業深度
3. 從唯識學「八識」的角度分析用戶問題根源
4. 提供具體可行的方法，而非表面的開示
5. 適當引用經文支持觀點，使用完整出處格式：
   - 直接引用：「出處：《經名》，原文：「引用原文」，CBETA網址：https://cbetaonline.dila.edu.tw/zh/[經文ID]」
   - 相關參考：「相關資料：《經名》，CBETA網址：https://cbetaonline.dila.edu.tw/zh/[經文ID]」
6. 回應文字控制在300-400字內，簡潔有力

請以專業而親切的方式回應，注重深度分析和具體建議：
""")
        
        # 初始化提示模板 - 用於分類用戶認知層級
        self.classification_prompt = ChatPromptTemplate.from_template("""
您是「菩薩小老師」，一位善於理解用戶需求的佛法智慧導師。請根據用戶的問題，判斷其修行階段和問題類型。

用戶問題：{user_query}

修行階段分類：
1. 初入門階段：對佛法知識尚淺，思維方式較為世俗，關注現實問題
2. 基礎修學階段：已接觸佛法基本概念，開始思考更深層問題
3. 深入理解階段：系統性學習佛法，能將佛法與生活連結
4. 行證實踐階段：有深厚佛法基礎，關注修行實踐和證悟過程

問題類型：
1. 煩惱解脫型：尋求解決現實煩惱的方法
2. 見解調和型：探討佛法與現代生活的融合
3. 生命意義型：對人生意義的探尋
4. 求法精進型：主動尋求佛法智慧和修行方法

請以JSON格式簡要分析用戶的階段和問題類型：
""")
        
        # 初始化四攝法策略選擇提示模板
        self.four_she_prompt = ChatPromptTemplate.from_template("""
您是「菩薩小老師」，一位精通四攝法的智慧導師。根據用戶的修行階段和問題類型，請選擇最適合的四攝法策略。

用戶修行階段：{user_level}
問題類型：{issue_type}

四攝法包括：
1. 布施（Dana）：通過無條件給予幫助建立關係，包括法布施、無畏布施和財布施
2. 愛語（Priyavacana）：以溫和、親切且循循善誘的言語引導
3. 利行（Arthakrtya）：提供實用方法，指導學習者走向正確的修行道路
4. 同事（Samanarthata）：與學習者站在同一立場，以同修身份交流，融入其處境

請考慮以下對應關係：
- 初入門階段的用戶通常適合布施和愛語為主的策略
- 基礎修學階段的用戶適合愛語和利行策略
- 深入理解和行證實踐階段的用戶適合利行和同事策略
- 煩惱解脫型問題適合愛語和利行
- 見解調和型問題適合利行和同事
- 生命意義型問題適合布施和愛語
- 求法精進型問題適合利行和同事

請指定最適合的策略（僅選一個）：
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
                    level = classification_result.get("認知層級", classification_result.get("user_level", classification_result.get("stage", classification_result.get("修行階段", "初入門階段"))))
                    issue_type = classification_result.get("問題類型", classification_result.get("issue_type", "煩惱解脫型"))
                    
                    classification_result = {
                        "level": level,
                        "type": issue_type
                    }
            else:
                # 無法解析JSON，使用默認值
                classification_result = {
                    "level": "初入門階段",
                    "type": "煩惱解脫型"
                }
            
            logger.info(f"用戶輸入分類結果: {classification_result}")
            return classification_result
            
        except Exception as e:
            logger.error(f"分類用戶輸入時出錯: {e}", exc_info=True)
            # 返回默認分類
            return {
                "level": "初入門階段",
                "type": "煩惱解脫型"
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
                if "初入門" in user_level or "一層" in user_level:
                    return "布施"
                elif "基礎修學" in user_level or "二層" in user_level:
                    return "愛語"
                elif "深入理解" in user_level or "三層" in user_level:
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
            response_content = response.content
            
            # 5. 整理回應
            references = []
            for text in relevant_texts:
                # 檢查回應中是否直接引用了這段經文
                is_direct_quote = False
                if text.get("text"):
                    # 檢查至少15個字符的片段是否出現在回應中
                    min_quote_length = 15
                    text_content = text.get("text", "")
                    
                    # 如果經文足夠長，嘗試找出可能的引用
                    if len(text_content) >= min_quote_length:
                        # 嘗試不同長度的片段
                        for start_idx in range(0, len(text_content) - min_quote_length + 1, 5):
                            end_idx = min(start_idx + 30, len(text_content))
                            segment = text_content[start_idx:end_idx].strip()
                            
                            # 避免太短的片段
                            if len(segment) < min_quote_length:
                                continue
                                
                            # 檢查這個片段是否出現在回應中（考慮標點符號和空格的差異）
                            clean_segment = ''.join(c for c in segment if c.isalnum())
                            clean_response = ''.join(c for c in response_content if c.isalnum())
                            
                            if len(clean_segment) >= min_quote_length and clean_segment in clean_response:
                                is_direct_quote = True
                                break
                
                # 檢查回應中是否提到了經名
                sutra_name = text.get("sutra", "") if not text.get("custom_document", False) else text.get("source", "")
                if sutra_name and f"《{sutra_name}》" in response_content:
                    is_direct_quote = True
                
                # 檢查出處標記
                if "出處：" in response_content and sutra_name and f"出處：《{sutra_name}》" in response_content:
                    is_direct_quote = True
                
                if text.get("custom_document", False) or text.get("custom", False):
                    # 自定義文檔參考
                    references.append({
                        "text": text.get("text", ""),
                        "source": text.get("source", ""),
                        "custom": True,
                        "is_direct_quote": is_direct_quote
                    })
                else:
                    # CBETA經文參考
                    references.append({
                        "text": text.get("text", ""),
                        "sutra": text.get("sutra", ""),
                        "sutra_id": text.get("sutra_id", ""),
                        "custom": False,
                        "is_direct_quote": is_direct_quote
                    })
            
            logger.info(f"生成回應，用戶修行階段: {user_level}, 策略: {four_she_strategy}")
            
            return {
                "text": response_content,
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
                "user_level": "初入門階段",
                "issue_type": "煩惱解脫型",
                "four_she_strategy": "愛語"
            }

    async def _get_chat_completion(self, messages: list) -> dict:
        """
        獲取OpenAI聊天完成
        
        Args:
            messages: 對話訊息列表
            
        Returns:
            dict: 回應數據
        """
        try:
            # 添加請求系統訊息
            system_message = {
                "role": "system", 
                "content": f"""
                你是「菩薩小老師」，一位結合唯識學智慧的佛法導師，以自然親切又有深度的方式引導學習者。

                用戶情況:
                - 修行階段: {self.user_level_descriptions[self.current_user_level]}
                - 問題類型: {self.issue_type_descriptions[self.current_issue_type]}
                - 溝通風格: {self.four_she_strategies[self.current_strategy]}

                回應核心原則：
                1. 簡潔自然的對話風格，避免說教，但保持專業深度
                2. 辨識用戶問題背後的真正意圖和心理需求
                3. 運用唯識學「八識」觀點分析用戶困境（前五識、意識、末那識和阿賴耶識）
                4. 提供具體可行的建議，不流於表面的開示
                5. 從「轉識成智」的角度引導用戶面對困難
                6. 保持客觀，避免主觀判斷

                回答結構（靈活運用，不必固定格式）：
                1. 簡要分析問題的根源（可從唯識學角度解釋）
                2. 提供具體實用的方法和建議
                3. 適當引用經典支持觀點，使用完整出處格式

                引用經典時：
                - 直接引用時：「出處：《經名》，原文：「引用原文」，CBETA網址：https://cbetaonline.dila.edu.tw/zh/經文ID」
                - 相關參考時：「相關資料：《經名》，CBETA網址：https://cbetaonline.dila.edu.tw/zh/經文ID」

                回答品質要求：
                - 精準把握用戶問題核心
                - 提供深入而非表面的分析
                - 給出可實踐的方法和建議
                - 維持溫暖親切但不失專業的語氣
                - 控制在300-400字，簡潔有力

                請記住：用戶尋求的不只是理論解釋，更需要能夠幫助他們理解自己的困境，並找到實際可行的解決方案。從唯識學的角度幫助他們認識自己的心識運作，以客觀的方式引導他們面對問題。
                """
            }
            
            # 組合最終消息列表
            final_messages = [system_message] + messages
            
            # 調用 OpenAI API
            response = self.client.chat.completions.create(
                model=settings.GPT_MODEL,
                messages=final_messages,
                temperature=0.7,
                max_tokens=1200,
                top_p=0.9,
                frequency_penalty=0.5,
                presence_penalty=0.2,
                response_format={"type": "json_object"},
            )
            
            # 解析JSON回應
            response_content = response.choices[0].message.content
            parsed_response = json.loads(response_content)
            
            # 確保必要的字段存在
            if "response" not in parsed_response:
                parsed_response["response"] = "抱歉，我無法生成有效的回應。請重新表述您的問題。"
            
            if "references" not in parsed_response:
                parsed_response["references"] = []
                
            if "suggestions" not in parsed_response:
                parsed_response["suggestions"] = []
            
            return parsed_response
        
        except Exception as e:
            logger.error(f"獲取聊天完成時出錯: {e}", exc_info=True)
            return {
                "response": "抱歉，處理您的請求時遇到問題。請稍後再試或重新表述您的問題。",
                "references": [],
                "suggestions": []
            }

# 單例模式實例
response_generator = ResponseGenerator() 