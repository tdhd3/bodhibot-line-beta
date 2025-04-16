import logging
from typing import List, Dict, Any, Optional
import json

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResponseGenerator:
    """
    回應生成器類別
    負責根據用戶問題和檢索到的經文生成回應
    """
    
    def __init__(self, vector_store, scripture_search, conversation_store):
        self.vector_store = vector_store
        self.scripture_search = scripture_search
        self.conversation_store = conversation_store
        
        # 初始化GPT模型
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.GPT_MODEL,
            temperature=0.3
        )
        
        # 初始化OpenAI客戶端，用於直接API調用
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 修行階段描述
        self.user_level_descriptions = {
            "初入門階段": "正在開始接觸佛法基礎知識，可能對核心概念如四聖諦、八正道還不熟悉",
            "基礎修行階段": "已了解基本教義，開始培養正念、禪修等修行習慣",
            "進階修行階段": "具備較深的教理理解，並有穩定的修行習慣，開始體驗內在轉化"
        }
        
        # 問題類型描述
        self.issue_type_descriptions = {
            "教理理解型": "尋求對佛教概念、經典或教義的澄清和理解",
            "修行方法型": "尋求具體的修行指導、禪修方法或實踐建議",
            "煩惱解脫型": "尋求化解生活中的痛苦、煩惱或情感困擾的方法",
            "信仰疑惑型": "對佛教某些信仰或主張產生疑惑或需要確認"
        }
        
        # 四攝法策略描述
        self.four_she_strategies = {
            "布施": "無條件給予清晰的知識和信息，保持客觀且豐富的資訊分享",
            "愛語": "使用溫和、鼓勵的語言，著重情感連接和心理支持",
            "利行": "提供實用的步驟化指導和具體方法，強調實際應用",
            "同事": "以平等態度進行深度理性討論，承認多元觀點，共同探索"
        }
        
        # 當前用戶狀態（默認值）
        self.current_user_level = "初入門階段"
        self.current_issue_type = "教理理解型"
        self.current_strategy = "布施"
        
        # 回應生成提示
        self.response_prompt = """你是一個名為「菩薩小老師」的佛學顧問AI，基於佛教教義與經典回答用戶問題。

用戶分析:
{classification}

用戶問題:
{query}

相關經文資料:
{sources}

請根據上述資訊，提供一個既有智慧又親切的回應。回應應直接針對用戶的核心問題，語調溫和、清晰且貼近日常對話。

回應需遵循這些指導原則:
1. 直接回答用戶問題，無需開場白或問候語
2. 內容應簡潔明瞭，避免冗長解釋
3. 使用現代、易懂的語言表達佛法概念
4. 根據用戶的程度調整專業術語的使用
5. 引用經文時要自然融入回答中，不要過於學術化，不再正文中標明出處
6. 避免在正文中使用「出處：《經名》」這樣的格式標記，系統會自動處理引用出處
7. 語調應親切、平等，不居高臨下
8. 鼓勵正面思考和實際行動，但避免命令式語氣
9. 回應長度應控制在200-300字之間
10. 如果用戶問題暗示他們處於困境，應給予溫暖支持
11. 引用原文時必須精確引用提供的資料，不要改變或簡化原文內容
12. 謙遜態度：遇到密法、深奧教義或無法確定的問題時，謹慎表達並建議用戶尋求正法道場或合格法師的指導
13. 限制：避免給出個人主觀意見、不提供外部非佛教相關資源或資訊，始終以佛法為中心進行指導

修行引導順序：根據用戶修行階段，按以下順序逐步引導：
1. 三世因果輪迴觀（適合初學者）
2. 出離心的培養
3. 慈悲心的修習
4. 斷十惡行十善
5. 菩提心的發起與實踐

經典推薦順序：
- 初學者階段：優先推薦《金剛經》或《普賢行願品》
- 中階修行者：可推薦《楞嚴經》《地藏經》
- 進階修行者：《法華經》《摩訶止觀》等

關於引用：
- 如有引用經文，請自然融入回答中，無需標明出處
- 系統將自動為用戶提供CBETA鏈接，不需要你標註CBETA編號
- 避免使用「出處：」或「引用：」等標記，保持回答的流暢性

最後一段可以提供1-2個實用建議或思考方向，或引導向進一步的學習資源，但避免說教。

回應:
"""
        
        # 用戶分析提示
        self.classification_prompt = """作為佛教智慧顧問「菩薩小老師」，請深入分析以下用戶提問，以便更全面地理解其需求和修行狀態。

用戶提問:
{query}

請提供全面的用戶分析，著重理解：
1. 用戶的修行程度 (初學者、有一定基礎、進階修行者)
2. 用戶的情感狀態 (困惑、痛苦、好奇、尋求確認等)
3. 問題的出發點與真正關心的核心問題
4. 問題背後可能隱藏的擔憂、煩惱或期望
5. 用戶提問的真實動機和生活情境
6. 用戶可能的文化背景和思維模式
7. 適合的回應深度和專業度

請以第三人稱撰寫一段分析，避免使用「我認為」等字眼。分析應該簡潔但深入，長度約150-250字。基於佛法的觀點進行分析，但避免急於給出建議，這僅是分析階段。

分析結果:"""
        
        # 四攝選擇提示
        self.four_she_prompt = """基於以下用戶分析和問題，請從佛教四攝法（布施、愛語、利行、同事）中選擇最合適的溝通策略。

用戶分析:
{user_analysis}

用戶提問:
{query}

請深入理解用戶的真實需求、心理狀態和修行程度，然後從以下四種策略中選擇最適合的一種：

1. 布施（Dana）：無條件給予知識和智慧
   - 適合：純粹尋求資訊的用戶、初學者、好奇心驅動的提問
   - 特點：直接提供清晰的知識，不附加條件

2. 愛語（Priyavacana）：溫和、鼓勵的語言
   - 適合：正經歷困難、情緒低落、需要心理支持的用戶
   - 特點：溫暖關懷的語調，重視情感連接，給予鼓勵

3. 利行（Arthakrtya）：提供實用的建議和方法
   - 適合：尋求實踐指導、具體修行方法的用戶
   - 特點：實用性強，提供步驟化指導，著重解決方案

4. 同事（Samanarthata）：以平等的態度分享經驗
   - 適合：進階修行者、質疑者、或需要深度交流的用戶
   - 特點：平等對話，理性討論，承認多元觀點

請只回答一個最適合的策略名稱（布施、愛語、利行或同事）："""
        
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
                query=user_query
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
    
    async def select_four_she_strategy(self, user_analysis: str, query: str) -> str:
        """
        根據用戶認知層級和問題類型選擇四攝法策略
        
        Args:
            user_analysis: 用戶分析
            query: 用戶問題
            
        Returns:
            str: 選擇的四攝法策略
        """
        try:
            # 準備提示
            four_she_prompt = self.four_she_prompt.format(
                user_analysis=user_analysis,
                query=query
            )
            
            # 調用LLM
            response = self.llm.invoke(four_she_prompt)
            
            strategy = response.content.strip()
            logger.info(f"選擇的四攝法策略: {strategy}")
            return strategy
        except Exception as e:
            logger.error(f"選擇四攝法策略時出錯: {e}")
            return "布施"  # 預設選擇布施
    
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
            user_motivation = classification.get("motivation", "尋求佛法智慧指導")
            approach_suggestion = classification.get("approach_suggestion", "")
            
            # 記錄更詳細的用戶分析以便調整回應
            logger.info(f"用戶分析 - 階段: {user_level}, 類型: {issue_type}, 動機: {user_motivation}")
            
            # 2. 選擇四攝法策略
            four_she_strategy = await self.select_four_she_strategy(user_level, issue_type)
            
            # 3. 查詢相關經文 (使用重排序功能)
            use_rerank = True  # 默認啟用重排序
            use_hybrid = True  # 默認啟用混合排序策略
            
            # 檢查是否有特定的需要精確匹配的關鍵詞
            if any(kw in user_query.lower() for kw in ["引用", "原文", "確切", "精確"]):
                # 對於要求精確引用的查詢，降低多樣性權重
                use_hybrid = False
                logger.info("檢測到用戶需要精確引用，關閉混合排序策略")
            
            try:
                # 嘗試使用新的經文檢索方法（帶重排序）
                relevant_texts = await self.scripture_search.search_by_query(
                    user_query, 
                    limit=5,
                    use_rerank=use_rerank,
                    use_hybrid=use_hybrid
                )
            except Exception as e:
                # 如果新方法失敗，記錄詳細錯誤並回退到標準搜索
                logger.warning(f"使用帶重排序的檢索方法失敗: {str(e)}，回退到標準搜索")
                try:
                    # 嘗試不使用重排序
                    relevant_texts = await self.scripture_search.search_by_query(
                        user_query, 
                        limit=5,
                        use_rerank=False,
                        use_hybrid=False
                    )
                except Exception as e2:
                    # 如果標準搜索也失敗，使用最基本的參數
                    logger.error(f"標準搜索也失敗: {str(e2)}，使用最基本檢索方法")
                    relevant_texts = await self.scripture_search.search_by_query(user_query, limit=5)
            
            # 準備經文文本用於提示
            formatted_texts = []
            for i, text in enumerate(relevant_texts):
                if text.get("custom", False):
                    # 自定義文檔
                    formatted_texts.append(f"{i+1}. 自定義文檔《{text.get('source', '')}》:\n{text.get('text', '')}")
                else:
                    # CBETA經文
                    formatted_texts.append(f"{i+1}. 經典《{text.get('sutra', '')}》(ID: {text.get('sutra_id', '')}):\n{text.get('text', '')}")
            
            texts_str = "\n\n".join(formatted_texts) if formatted_texts else "未找到相關經文。"
            
            # 獲取對話歷史
            chat_history = await self.conversation_store.get_conversation_history(user_id)
            history_context = ""
            
            # 格式化對話歷史
            if chat_history and len(chat_history) > 0:
                # 只使用最近的幾輪對話
                history_limit = getattr(settings, "HISTORY_LIMIT", 5)
                recent_history = chat_history[-history_limit*2:]  # 用戶和機器人的消息對
                
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
                query=user_query,
                classification=f"階段: {user_level}, 類型: {issue_type}, 動機: {user_motivation}",
                sources=texts_str
            )
            
            # 如果有對話歷史，加到提示中
            if history_context:
                response_prompt = response_prompt + "\n\n" + history_context + "\n\n請考慮上述對話歷史，保持一致性地回應用戶的問題。"
            
            # 調用LLM
            response = self.llm.invoke(response_prompt)
            response_content = response.content
            
            # 存儲對話
            await self.conversation_store.store_message(user_id, "user", user_query)
            await self.conversation_store.store_message(user_id, "assistant", response_content)
            
            # 5. 整理回應
            references = []
            
            # 從sutra_retriever中獲取經典別名映射，如果可以獲取的話
            sutra_aliases = {}
            try:
                from app.services.sutra_retriever import sutra_retriever
                sutra_aliases = getattr(sutra_retriever, 'sutra_aliases', {})
            except ImportError:
                logger.warning("無法導入sutra_retriever獲取經典別名")
                
            for text in relevant_texts:
                # 檢查回應中是否直接引用了這段經文
                is_direct_quote = False
                if text.get("text"):
                    # 檢查至少8個字符的片段是否出現在回應中
                    min_quote_length = 8
                    text_content = text.get("text", "")
                    
                    # 如果經文足夠長，嘗試找出可能的引用
                    if len(text_content) >= min_quote_length:
                        # 嘗試不同長度的片段
                        for start_idx in range(0, len(text_content) - min_quote_length + 1, 3):
                            end_idx = min(start_idx + 20, len(text_content))
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
                
                # 檢查回應中是否提到了經名（包括別名）
                sutra_id = text.get("sutra_id", "")
                sutra_name = text.get("sutra", "") if not text.get("custom", False) else text.get("source", "")
                
                # 檢查所有可能的經名版本
                possible_names = [sutra_name]
                if sutra_id in sutra_aliases:
                    possible_names.extend(sutra_aliases[sutra_id])
                
                for name in possible_names:
                    if name and (f"《{name}》" in response_content or name in response_content):
                        is_direct_quote = True
                        break
                
                # 添加相關性分數，確保檢索到的文本始終被添加到引用列表
                relevance_score = text.get("score", 0) if text.get("score") is not None else (0.9 if is_direct_quote else 0.7)
                
                if text.get("custom", False):
                    # 自定義文檔參考
                    references.append({
                        "text": text.get("text", ""),
                        "source": text.get("source", ""),
                        "custom": True,
                        "is_direct_quote": is_direct_quote,
                        "relevance": relevance_score
                    })
                else:
                    # CBETA經文參考
                    references.append({
                        "text": text.get("text", ""),
                        "sutra": text.get("sutra", ""),
                        "sutra_id": text.get("sutra_id", ""),
                        "custom": False,
                        "is_direct_quote": is_direct_quote,
                        "relevance": relevance_score
                    })
            
            logger.info(f"生成回應，用戶修行階段: {user_level}, 策略: {four_she_strategy}")
            
            return {
                "text": response_content,
                "references": references,
                "user_level": user_level,
                "issue_type": issue_type,
                "four_she_strategy": four_she_strategy,
                "motivation": user_motivation,
                "approach_suggestion": approach_suggestion
            }
            
        except Exception as e:
            logger.error(f"生成回應時出錯: {e}", exc_info=True)
            # 返回錯誤回應
            return {
                "text": "很抱歉，我在處理您的問題時遇到了困難。請稍後再嘗試，或者換一種方式提問。",
                "references": [],
                "user_level": "初入門階段",
                "issue_type": "煩惱解脫型",
                "four_she_strategy": "布施",
                "motivation": "尋求佛法智慧指導",
                "approach_suggestion": ""
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
                你是「菩薩小老師」，一位結合唯識學智慧的佛法導師，以簡短精準又有深度的方式引導學習者。

                用戶情況:
                - 修行階段: {self.user_level_descriptions[self.current_user_level]}
                - 問題類型: {self.issue_type_descriptions[self.current_issue_type]}
                - 溝通風格: {self.four_she_strategies[self.current_strategy]}

                回應核心原則：
                1. 簡短精準：針對簡單問題回答控制在150-250字內，涉及深度佛法探討時延長至500字
                2. 修行引導：按照「三世因果輪迴觀→出離心→慈悲心→斷十惡行十善→菩提心」的順序循序漸進
                3. 唯識觀照：應用唯識學方法幫助用戶觀察自身心靈與行為模式
                4. 引用方式：在正文中自然引用經文但不標註出處，系統會自動處理引用格式
                5. 避免特殊格式：不使用影響閱讀的特殊標記或排版符號
                6. 謙遜態度：遇到密法、深奧教義或無法確定的問題時，謹慎表達並建議用戶尋求正法道場或合格法師的指導
                7. 限制：避免給出個人主觀意見、不提供外部非佛教相關資源或資訊，始終以佛法為中心進行指導

                經典推薦順序：
                - 初學者階段：優先推薦《金剛經》或《普賢行願品》
                - 中階修行者：可推薦《楞嚴經》《地藏經》
                - 進階修行者：《法華經》《摩訶止觀》等

                關於引用：
                - 如有引用經文，請自然融入回答中，無需標明出處
                - 系統將自動為用戶提供CBETA鏈接，不需要你標註CBETA編號
                - 避免使用「出處：」或「引用：」等標記，保持回答的流暢性

                回答品質要求：
                - 精準把握用戶問題核心
                - 提供實用的唯識觀察方法
                - 給出明確可行的修行建議
                - 針對簡單問題，控制在250字以內
                - 針對深度佛法探討，可擴展至500字
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
# 修改單例創建方式，延遲導入依賴並提供必要的參數
def get_response_generator():
    from app.services.vector_store import vector_store
    from app.services.scripture_search import scripture_search
    from app.services.conversation_store import conversation_store
    
    return ResponseGenerator(
        vector_store=vector_store,
        scripture_search=scripture_search,
        conversation_store=conversation_store
    )

response_generator = get_response_generator() 