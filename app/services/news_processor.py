import requests
import logging
import random
from typing import Dict, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.core.config import settings

# 配置日誌
logger = logging.getLogger(__name__)

class NewsProcessor:
    """新聞處理器，用於獲取最新新聞並從佛教角度提供觀點"""
    
    def __init__(self, api_key: str = None):
        """
        初始化新聞處理器
        Args:
            api_key: GNews API的API密鑰
        """
        self.api_key = api_key or settings.GNEWS_API_KEY
        # GNews API
        self.news_api_url = "https://gnews.io/api/v4/top-headlines"
        # 台灣中央社RSS
        self.cna_rss_url = "https://www.cna.com.tw/RSS/MainNews.aspx"
        
        # 備用新聞源 (如果API不可用)
        self.fallback_urls = [
            "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
            "https://www.ettoday.net/rss/news-list.xml",
            "https://feeds.feedburner.com/pts_news"
        ]
        
    def _fetch_news(self) -> Optional[List[Dict]]:
        """
        從GNews API獲取新聞
        Returns:
            新聞字典列表或None
        """
        if not self.api_key:
            logger.warning("未設置GNews API密鑰，使用備用新聞源")
            return self._fetch_fallback_news()
            
        try:
            # 添加積極正面的關鍵詞和類別
            positive_topics = ["國際關係", "經濟發展", "政策改革", "科技創新", "文化交流"]
            selected_topic = random.choice(positive_topics)
            
            params = {
                "token": self.api_key,
                "lang": "zh",
                "country": "tw",
                "max": 10,
                "q": selected_topic,  # 添加正面關鍵詞
                "sortby": "relevance"  # 按相關性排序
            }
            
            response = requests.get(self.news_api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                if articles:
                    # 過濾新聞，移除可能包含負面內容的標題
                    negative_keywords = ["死亡", "殺害", "事故", "災難", "喪生", "墜機", "槍擊", "自殺", "失蹤", "罪犯"]
                    filtered_articles = [
                        article for article in articles 
                        if not any(keyword in article.get("title", "").lower() for keyword in negative_keywords)
                    ]
                    
                    # 如果過濾後仍有足夠的新聞
                    if len(filtered_articles) >= 3:
                        # 隨機選擇三條不同的新聞
                        selected_articles = random.sample(filtered_articles, 3)
                    elif filtered_articles:
                        selected_articles = filtered_articles
                    else:
                        # 如果過濾後沒有新聞，嘗試使用備用新聞源
                        return self._fetch_fallback_news()
                        
                    news_list = []
                    for article in selected_articles:
                        news_list.append({
                            "title": article.get("title", ""),
                            "description": article.get("description", ""),
                            "url": article.get("url", ""),
                            "source": article.get("source", {}).get("name", ""),
                            "category": selected_topic  # 添加類別信息
                        })
                    return news_list
            elif response.status_code == 401:
                logger.warning("GNews API密鑰無效或已過期，使用備用新聞源")
                return self._fetch_fallback_news()
            else:
                logger.warning(f"GNews API請求失敗，狀態碼: {response.status_code}，使用備用新聞源")
                return self._fetch_fallback_news()
            
        except Exception as e:
            logger.error(f"從GNews API獲取新聞時發生錯誤: {str(e)}，使用備用新聞源")
            return self._fetch_fallback_news()
            
    def _fetch_fallback_news(self) -> Optional[List[Dict]]:
        """
        從備用源獲取新聞
        Returns:
            新聞字典列表或None
        """
        try:
            # 嘗試使用中央社RSS
            response = requests.get(self.cna_rss_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    # 解析RSS
                    root = ET.fromstring(response.content)
                    items = root.findall(".//item")
                    
                    if items and len(items) >= 3:
                        # 過濾負面新聞
                        negative_keywords = ["死亡", "殺害", "事故", "災難", "喪生", "墜機", "槍擊", "自殺", "失蹤", "罪犯"]
                        filtered_items = []
                        
                        # 首先找出國際政治、經濟相關新聞
                        positive_categories = ["國際", "兩岸", "政治", "產經", "證券", "科技", "文化"]
                        
                        # 優先選擇符合類別的新聞
                        for item in items:
                            title = item.find("title").text if item.find("title") is not None else ""
                            # 檢查是否包含正面類別
                            if any(category in title for category in positive_categories):
                                # 確保不包含負面關鍵詞
                                if not any(keyword in title.lower() for keyword in negative_keywords):
                                    filtered_items.append(item)
                        
                        # 如果符合類別的新聞不足3條，再從其他新聞中選擇
                        if len(filtered_items) < 3:
                            for item in items:
                                title = item.find("title").text if item.find("title") is not None else ""
                                if item not in filtered_items and not any(keyword in title.lower() for keyword in negative_keywords):
                                    filtered_items.append(item)
                                if len(filtered_items) >= 3:
                                    break
                        
                        # 如果過濾後仍有足夠的新聞
                        if filtered_items and len(filtered_items) >= 3:
                            # 隨機選擇三條新聞
                            selected_items = random.sample(filtered_items, 3)
                        elif filtered_items:
                            selected_items = filtered_items
                        else:
                            # 如果沒有符合條件的新聞，選擇原始項目
                            selected_items = random.sample(items, 3)
                        
                        news_list = []
                        for item in selected_items:
                            title = item.find("title").text if item.find("title") is not None else ""
                            description = item.find("description").text if item.find("description") is not None else ""
                            link = item.find("link").text if item.find("link") is not None else ""
                            
                            # 清理描述中的HTML標籤
                            description = re.sub(r'<[^>]+>', '', description)
                            
                            # 確定新聞類別
                            category = "一般新聞"
                            for cat in positive_categories:
                                if cat in title:
                                    category = cat
                                    break
                            
                            news_list.append({
                                "title": title,
                                "description": description,
                                "url": link,
                                "source": "中央社",
                                "category": category
                            })
                        return news_list
                except ET.ParseError:
                    logger.warning("解析中央社RSS時出錯，嘗試其他備用源")
                    
            # 如果中央社不可用，嘗試其他備用源
            for url in self.fallback_urls:
                try:
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        # 解析RSS
                        root = ET.fromstring(response.content)
                        items = root.findall(".//item")
                        
                        if items and len(items) >= 3:
                            # 過濾負面新聞
                            negative_keywords = ["死亡", "殺害", "事故", "災難", "喪生", "墜機", "槍擊", "自殺", "失蹤", "罪犯"]
                            filtered_items = []
                            
                            # 優先選擇國際政治、經濟相關新聞
                            positive_categories = ["國際", "兩岸", "政治", "產經", "證券", "科技", "文化"]
                            
                            for item in items:
                                title = item.find("title").text if item.find("title") is not None else ""
                                # 檢查是否包含正面類別
                                if any(category in title for category in positive_categories):
                                    # 確保不包含負面關鍵詞
                                    if not any(keyword in title.lower() for keyword in negative_keywords):
                                        filtered_items.append(item)
                            
                            # 如果符合類別的新聞不足3條，再從其他新聞中選擇
                            if len(filtered_items) < 3:
                                for item in items:
                                    title = item.find("title").text if item.find("title") is not None else ""
                                    if item not in filtered_items and not any(keyword in title.lower() for keyword in negative_keywords):
                                        filtered_items.append(item)
                                    if len(filtered_items) >= 3:
                                        break
                            
                            # 如果過濾後仍有足夠的新聞
                            if filtered_items and len(filtered_items) >= 3:
                                # 隨機選擇三條新聞
                                selected_items = random.sample(filtered_items, 3)
                            elif filtered_items:
                                selected_items = filtered_items
                            else:
                                # 如果沒有符合條件的新聞，選擇原始項目
                                selected_items = random.sample(items, 3)
                            
                            news_list = []
                            for item in selected_items:
                                title = item.find("title").text if item.find("title") is not None else ""
                                description = item.find("description").text if item.find("description") is not None else ""
                                link = item.find("link").text if item.find("link") is not None else ""
                                source = url.split("/")[2]
                                
                                # 清理描述中的HTML標籤
                                description = re.sub(r'<[^>]+>', '', description)
                                
                                # 確定新聞類別
                                category = "一般新聞"
                                for cat in positive_categories:
                                    if cat in title:
                                        category = cat
                                        break
                                
                                news_list.append({
                                    "title": title,
                                    "description": description,
                                    "url": link,
                                    "source": source,
                                    "category": category
                                })
                            return news_list
                except (ET.ParseError, requests.RequestException) as e:
                    logger.warning(f"從 {url} 獲取新聞時出錯: {str(e)}")
                    continue
                        
            logger.error("所有新聞源嘗試失敗")
            return None
            
        except Exception as e:
            logger.error(f"從備用源獲取新聞時發生錯誤: {str(e)}")
            return None

    def _create_short_url(self, long_url: str) -> str:
        """
        生成短網址（簡單版）
        Args:
            long_url: 長網址
        Returns:
            短網址或原始網址
        """
        try:
            # 這裡可以集成實際的短網址服務，如TinyURL或Bitly
            # 目前僅返回原始URL
            return long_url
        except Exception as e:
            logger.error(f"生成短網址時發生錯誤: {str(e)}")
            return long_url
            
    async def get_daily_news(self, llm: ChatOpenAI = None) -> List[Dict]:
        """
        獲取每日新聞並添加觀點
        Args:
            llm: 語言模型（如果未提供，則使用配置中的默認模型）
        Returns:
            包含新聞標題、內容、連結和觀點的字典列表
        """
        try:
            # 如果未提供LLM，使用默認設置創建一個
            if llm is None:
                llm = ChatOpenAI(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model=settings.GPT_MODEL,
                    temperature=0.7
                )
            
            # 嘗試獲取新聞
            news_list = self._fetch_news()
            if not news_list:
                # 使用備用新聞
                news_list = self._fetch_fallback_news()
                
            if not news_list:
                # 如果仍然沒有新聞，返回預設消息
                return [{
                    "title": "無法獲取今日新聞",
                    "content": "當下即是最好的新聞",
                    "url": "",
                    "perspective": "我們可以專注於當下，觀察周圍發生的事情，理解世界的運作方式。"
                }]
            
            # 針對每條新聞生成觀點    
            result_news = []
            for news in news_list:
                # 使用LLM生成觀點
                perspective = await self._generate_buddhist_perspective(news, llm)
                
                result_news.append({
                    "title": news.get("title", "今日新聞"),
                    "content": news.get("description", ""),
                    "url": news.get("url", ""),
                    "source": news.get("source", ""),
                    "perspective": perspective
                })
                
            return result_news
            
        except Exception as e:
            logger.error(f"獲取新聞時發生錯誤: {str(e)}")
            # 返回預設消息
            return [{
                "title": "每日省思",
                "content": "反思我們與世界的連結",
                "url": "",
                "perspective": "在紛繁的世界中，我們可以學習如何保持平靜和智慧，關注正向改變。"
            }]
            
    async def _generate_buddhist_perspective(self, news: Dict, llm: ChatOpenAI) -> str:
        """
        生成佛教觀點
        Args:
            news: 新聞字典
            llm: 語言模型
        Returns:
            觀點
        """
        try:
            title = news.get("title", "")
            content = news.get("description", "")
            category = news.get("category", "一般新聞")
            
            prompt = f"""角色設定：
你是一位智慧導師，擅長從客觀角度審視當前國際情勢和國內政經發展，提供中立而富有啟發性的觀點。

[新聞標題]: {title}
[新聞類別]: {category}
[新聞內容]: {content}

請生成一段不超過100字的客觀省思，要求：
1. 保持政治、宗教中立，不偏向任何立場
2. 著重於「因緣關聯」和「無常變化」等佛法智慧在該新聞中的體現
3. 提供啟發性的觀點，引導讀者深入思考事件背後的本質
4. 若是經濟或政治新聞，可從「中道」與「平衡」的角度進行解讀
5. 若是國際關係新聞，可從「相互依存」和「慈悲包容」的角度分析
6. 避免使用過多佛教專有名詞，保持通俗易懂

直接提供客觀省思內容，無需標題或額外格式。"""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
            
        except Exception as e:
            logger.error(f"生成觀點時發生錯誤: {str(e)}")
            # 返回預設觀點
            return "這則新聞提醒我們，世間萬物相互關聯，每一個事件都是因緣和合的結果。保持開放客觀的心態去理解事件的多面向，以智慧洞察事物的本質，才能在複雜的世界中找到平衡與中道。"
            
    def format_daily_dharma(self, news_list: List[Dict]) -> str:
        """
        格式化每日法語
        Args:
            news_list: 新聞字典列表
        Returns:
            格式化的每日法語
        """
        formatted_text = f"📰 今日國際與政經觀察 - {datetime.now().strftime('%Y/%m/%d')}\n{'-'*20}\n\n"
        
        # 檢查是否為列表
        if not isinstance(news_list, list):
            news_list = [news_list]
            
        # 處理每條新聞
        for i, news in enumerate(news_list):
            title = news.get("title", "今日觀察")
            perspective = news.get("perspective", "")
            url = news.get("url", "")
            content = news.get("description", "")
            category = news.get("category", "一般新聞")
            source = news.get("source", "")
            
            # 確保內容不會太長
            if len(content) > 100:
                content = content[:97] + "..."
            
            # 添加新聞標題和類別
            formatted_text += f"【{category}】{title}\n\n"
            
            # 分成段落顯示內容和觀點
            formatted_text += f"📊 要點：{content}\n\n"
            
            formatted_text += f"🔍 客觀省思：{perspective}\n\n"
            
            # 添加思考問題，根據新聞類別調整
            if "國際" in category or "兩岸" in category:
                formatted_text += f"💭 思考：這些國際發展如何體現「相互依存」的道理？\n\n"
            elif "政治" in category:
                formatted_text += f"💭 思考：如何以「中道」的智慧理解這一政治現象？\n\n"
            elif "經濟" in category or "產經" in category or "證券" in category:
                formatted_text += f"💭 思考：經濟變化中，如何保持平衡心態？\n\n"
            else:
                formatted_text += f"💭 思考：從客觀角度，我們能從中獲得什麼啟示？\n\n"
            
            if i < len(news_list) - 1:
                formatted_text += f"{'-'*20}\n\n"
        
        # 添加簡潔的原文引用標題
        if len(news_list) > 0:
            formatted_text += f"{'-'*20}\n"
            formatted_text += "📋 原始來源:\n"
            for i, news in enumerate(news_list):
                title = news.get("title", "")
                source = news.get("source", "")
                
                if title and source:
                    # 只顯示標題和來源，不顯示URL
                    formatted_text += f"{i+1}. {source}: {title.split(' - ')[0]}\n"
                    
            formatted_text += "\n"
        
        # 添加結尾語
        formatted_text += "🌏 願以智慧之眼觀世界，以平等之心待萬物"
            
        return formatted_text
    
    async def get_formatted_news(self) -> str:
        """
        獲取格式化的新聞
        Returns:
            格式化的新聞文本
        """
        try:
            news_list = await self.get_daily_news()
            return self.format_daily_dharma(news_list)
        except Exception as e:
            logger.error(f"獲取格式化新聞時發生錯誤: {str(e)}")
            return "無法獲取今日新聞，請稍後再試。"

# 單例模式實例
news_processor = NewsProcessor() 