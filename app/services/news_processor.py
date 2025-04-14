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
            return None
            
        try:
            params = {
                "token": self.api_key,
                "lang": "zh",
                "country": "tw",
                "max": 10
            }
            
            response = requests.get(self.news_api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                if articles:
                    # 隨機選擇三條不同的新聞
                    if len(articles) >= 3:
                        selected_articles = random.sample(articles, 3)
                    else:
                        selected_articles = articles
                        
                    news_list = []
                    for article in selected_articles:
                        news_list.append({
                            "title": article.get("title", ""),
                            "description": article.get("description", ""),
                            "url": article.get("url", ""),
                            "source": article.get("source", {}).get("name", "")
                        })
                    return news_list
            
            logger.warning(f"GNews API請求失敗，狀態碼: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"從GNews API獲取新聞時發生錯誤: {str(e)}")
            return None
            
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
                        # 隨機選擇三條新聞
                        selected_items = random.sample(items, 3)
                        
                        news_list = []
                        for item in selected_items:
                            title = item.find("title").text if item.find("title") is not None else ""
                            description = item.find("description").text if item.find("description") is not None else ""
                            link = item.find("link").text if item.find("link") is not None else ""
                            
                            # 清理描述中的HTML標籤
                            description = re.sub(r'<[^>]+>', '', description)
                            
                            news_list.append({
                                "title": title,
                                "description": description,
                                "url": link,
                                "source": "中央社"
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
                            # 隨機選擇三條新聞
                            selected_items = random.sample(items, 3)
                            
                            news_list = []
                            for item in selected_items:
                                title = item.find("title").text if item.find("title") is not None else ""
                                description = item.find("description").text if item.find("description") is not None else ""
                                link = item.find("link").text if item.find("link") is not None else ""
                                source = url.split("/")[2]
                                
                                # 清理描述中的HTML標籤
                                description = re.sub(r'<[^>]+>', '', description)
                                
                                news_list.append({
                                    "title": title,
                                    "description": description,
                                    "url": link,
                                    "source": source
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
            
            prompt = f"""角色設定：
你是一位智慧導師，擅長從日常新聞中提取深刻哲理，提供簡潔有力的生活啟示。你的回應需保持中立、富有啟發性，同時避免宗教色彩過重。

[新聞標題]: {title}
[新聞內容]: {content}

請生成一段不超過100字的省思文本，要求：
1. 語氣平實但富有哲理
2. 包含正向行動啟示
3. 適度使用佛教觀點，但避免過多專有名詞
4. 保持開放性讓讀者有思考空間

直接提供省思內容，無需標題或額外格式。"""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
            
        except Exception as e:
            logger.error(f"生成觀點時發生錯誤: {str(e)}")
            # 返回預設觀點
            return "從這則新聞，我們反思如何在混沌中找到內在的平靜，並培養面對挑戰的智慧。世間萬物皆是無常變化，學習放下執著，才能獲得真正的自在。"
            
    def format_daily_dharma(self, news_list: List[Dict]) -> str:
        """
        格式化每日法語
        Args:
            news_list: 新聞字典列表
        Returns:
            格式化的每日法語
        """
        formatted_text = f"📰 今日省思 - {datetime.now().strftime('%Y/%m/%d')}\n{'-'*20}\n\n"
        
        # 檢查是否為列表
        if not isinstance(news_list, list):
            news_list = [news_list]
            
        # 處理每條新聞
        for i, news in enumerate(news_list):
            title = news.get("title", "今日省思")
            perspective = news.get("perspective", "")
            url = news.get("url", "")
            content = news.get("content", "")
            
            # 確保內容不會太長
            if len(content) > 100:
                content = content[:97] + "..."
            
            # 添加新聞標題和觀點
            formatted_text += f"【新聞{i+1}】{title}\n\n"
            
            # 分成段落顯示內容和觀點
            formatted_text += f"📖 摘要：{content}\n\n"
            
            formatted_text += f"🧘‍♀️ 心靈鏡鑑：{perspective}\n\n"
            
            # 添加思考問題
            formatted_text += f"💭 今日提問：如何將這份覺察帶入日常？\n\n"
            
            if i < len(news_list) - 1:
                formatted_text += f"{'-'*20}\n\n"
        
        # 添加原文連結
        if len(news_list) > 0 and any(news.get("url") for news in news_list):
            formatted_text += f"{'-'*20}\n"
            formatted_text += "🔗 原始新聞:\n"
            for i, news in enumerate(news_list):
                url = news.get("url", "")
                if url:
                    # 創建短網址
                    short_url = self._create_short_url(url)
                    formatted_text += f"{i+1}. {short_url}\n"
            
            formatted_text += "\n"
        
        # 添加結尾語
        formatted_text += "🌱 願今日省思成為明日的行動力"
            
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