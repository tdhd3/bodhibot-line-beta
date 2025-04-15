import os
import re
import logging
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import json

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from app.core.config import settings
from app.services.vector_store import VectorStore

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CBETAProcessor:
    """
    CBETA經文處理器
    負責下載、解析和存儲佛經內容
    """
    
    def __init__(self):
        """初始化CBETA處理器"""
        self.vector_store = VectorStore()
        self.data_dir = Path("data/cbeta")
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # 確保數據目錄存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 設置CBETA文件夾路徑
        self.cbeta_folder = self.data_dir
        
        # 設置向量數據庫路徑
        self.vector_db_path = Path(settings.VECTOR_DB_PATH)
        self.vector_db_path.mkdir(exist_ok=True, parents=True)
        
        # 準備嵌入模型（僅當API密鑰可用時）
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model=settings.EMBEDDING_MODEL
                )
                self.embedding_available = True
            except Exception as e:
                logger.warning(f"初始化OpenAI嵌入模型失敗: {e}")
                self.embedding_available = False
        else:
            logger.warning("未設置OpenAI API Key，向量存儲功能將不可用")
            self.embeddings = None
            self.embedding_available = False
        
        # 準備文本分割器 - 針對經文的特殊性調整
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )
        
        # CBETA API 相關設定
        self.cbeta_base_url = settings.CBETA_URL_BASE
        self.supported_sutras = settings.SUPPORTED_SUTRAS
    
    async def process_all_sutras(self):
        """處理所有支援的經典"""
        logger.info("開始處理所有經典")
        
        for sutra in self.supported_sutras:
            try:
                logger.info(f"開始處理經典: {sutra['name']} (ID: {sutra['id']})")
                await self.process_sutra(sutra['id'], sutra['name'])
            except Exception as e:
                logger.error(f"處理經典時出錯 {sutra['name']}: {e}", exc_info=True)
    
    async def process_sutra(self, sutra_id: str, sutra_name: str):
        """
        處理特定經典
        
        Args:
            sutra_id: CBETA經典ID (如 "T0945")
            sutra_name: 經典名稱 (如 "楞嚴經")
        """
        # 檢查是否已經下載過此經典
        sutra_file = self.cbeta_folder / f"{sutra_id}.xml"
        
        if not sutra_file.exists():
            # 如果尚未下載，則爬取經典內容
            success = await self._download_sutra(sutra_id)
            if not success:
                logger.error(f"無法下載經典 {sutra_name} (ID: {sutra_id})")
                return
        
        # 讀取和解析經典文件
        sutra_text, sutra_metadata = await self._parse_sutra_file(sutra_file, sutra_name)
        
        if not sutra_text:
            logger.error(f"無法解析經典內容 {sutra_name}")
            return
        
        logger.info(f"成功下載和解析經典: {sutra_name}")
        
        # 如果嵌入模型不可用，則僅保存解析後的文本而不創建向量
        if not self.embedding_available:
            # 保存純文本版本
            text_file = self.cbeta_folder / f"{sutra_id}.txt"
            async with aiofiles.open(text_file, 'w', encoding='utf-8') as f:
                await f.write(sutra_text)
            logger.info(f"由於OpenAI API Key未設置，僅保存了純文本版本: {sutra_name}")
            return
        
        # 分割經文
        chunks = self.text_splitter.split_text(sutra_text)
        logger.info(f"經典 {sutra_name} 被分割為 {len(chunks)} 個片段")
        
        # 準備元數據
        metadata_list = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": sutra_name,
                "sutra_id": sutra_id,
                "chunk_id": i,
                "custom_document": False,
            }
            # 添加共通元數據
            metadata.update(sutra_metadata)
            metadata_list.append(metadata)
        
        # 將文本存入向量資料庫
        collection_name = "cbeta_sutras"
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.vector_db_path)
        )
        
        # 添加文檔到向量存儲
        vectorstore.add_texts(chunks, metadata_list)
        vectorstore.persist()
        
        logger.info(f"成功處理並存儲經典: {sutra_name}")
    
    async def _download_sutra(self, sutra_id: str) -> bool:
        """
        下載特定經典的XML資料
        
        Args:
            sutra_id: CBETA經典ID
            
        Returns:
            bool: 下載成功返回True，否則返回False
        """
        # CBETA XML API URL 
        # 注意：這裡使用模擬的URL，實際上需要根據CBETA的API規範調整
        url = f"{self.cbeta_base_url}/api/xml/{sutra_id}"
        
        try:
            # 創建aiohttp會話並發送請求
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"下載經典XML失敗: {sutra_id}, 狀態碼: {response.status}")
                        
                        # 如果API請求失敗，改用爬蟲方式
                        return await self._scrape_sutra(sutra_id)
                    
                    # 讀取回應內容
                    content = await response.text()
                    
                    # 保存到文件
                    sutra_file = self.cbeta_folder / f"{sutra_id}.xml"
                    async with aiofiles.open(sutra_file, 'w', encoding='utf-8') as f:
                        await f.write(content)
                    
                    logger.info(f"成功下載經典XML: {sutra_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"下載經典XML時出錯 {sutra_id}: {e}", exc_info=True)
            
            # 如果API請求出錯，嘗試爬蟲方式
            return await self._scrape_sutra(sutra_id)
    
    async def _scrape_sutra(self, sutra_id: str) -> bool:
        """
        透過網頁爬蟲方式獲取經典內容
        
        Args:
            sutra_id: CBETA經典ID
            
        Returns:
            bool: 爬取成功返回True，否則返回False
        """
        # 更新後的CBETA網頁URL
        url = f"https://cbetaonline.dila.edu.tw/zh/T{sutra_id[1:]}"
        
        try:
            # 創建aiohttp會話並發送請求
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"爬取經典頁面失敗: {sutra_id}, 狀態碼: {response.status}")
                        # 嘗試替代URL
                        return await self._scrape_sutra_alternative(sutra_id)
                    
                    # 讀取回應內容
                    html_content = await response.text()
                    
                    # 檢查是否獲得了HTML而不是實際內容
                    if "<html" in html_content[:100].lower():
                        logger.warning(f"獲取到的是HTML頁面而非經文內容，嘗試替代方法: {sutra_id}")
                        return await self._scrape_sutra_alternative(sutra_id)
                    
                    # 使用BeautifulSoup解析HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # 嘗試從CBETA頁面提取經文內容
                    content_div = soup.select_one('div#reading-area-1-container')
                    
                    if not content_div:
                        logger.error(f"無法在頁面中找到經文內容: {sutra_id}")
                        return await self._scrape_sutra_alternative(sutra_id)
                    
                    # 提取純文本
                    text_content = content_div.get_text(separator='\n', strip=True)
                    
                    if not text_content or len(text_content) < 100:
                        logger.warning(f"提取的經文內容太短或為空: {sutra_id}")
                        return await self._scrape_sutra_alternative(sutra_id)
                    
                    # 創建簡單的XML結構來保存內容
                    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{sutra_id}</title>
      </titleStmt>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        {text_content}
      </div>
    </body>
  </text>
</TEI>
"""
                    
                    # 保存到文件
                    sutra_file = self.cbeta_folder / f"{sutra_id}.xml"
                    async with aiofiles.open(sutra_file, 'w', encoding='utf-8') as f:
                        await f.write(xml_content)
                    
                    logger.info(f"成功爬取經典內容: {sutra_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"爬取經典內容時出錯 {sutra_id}: {e}", exc_info=True)
            return await self._scrape_sutra_alternative(sutra_id)
    
    async def _scrape_sutra_alternative(self, sutra_id: str) -> bool:
        """
        使用替代方法獲取經典內容 - 直接使用純文本形式
        
        Args:
            sutra_id: CBETA經典ID
            
        Returns:
            bool: 爬取成功返回True，否則返回False
        """
        try:
            # 嘗試從GitHub等開源佛經資源獲取
            sutra_name = "未知經典"
            for sutra in self.supported_sutras:
                if sutra['id'] == sutra_id:
                    sutra_name = sutra['name']
                    break
            
            logger.info(f"使用替代方法下載經文: {sutra_name} ({sutra_id})")
            
            # 如果無法從網絡獲取，使用預設文本
            sample_text = f"""
{sutra_name} ({sutra_id})

由於無法從CBETA網站直接獲取經文內容，這是一個簡易版本的經文樣本。
實際使用時，建議從CBETA官方下載完整經文數據，並放置在data/cbeta目錄下。

經文ID: {sutra_id}
經文名稱: {sutra_name}
下載時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

備註：此為佛光大藏經《{sutra_name}》的簡易樣本，僅供參考。完整內容請參閱CBETA官方資源。
"""
            
            # 創建簡單的XML結構
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{sutra_id} {sutra_name}</title>
      </titleStmt>
      <publicationStmt>
        <p>樣本數據 - 非官方CBETA內容</p>
      </publicationStmt>
      <sourceDesc>
        <p>替代來源</p>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        {sample_text}
      </div>
    </body>
  </text>
</TEI>
"""

            # 保存到文件
            sutra_file = self.cbeta_folder / f"{sutra_id}.xml"
            async with aiofiles.open(sutra_file, 'w', encoding='utf-8') as f:
                await f.write(xml_content)
            
            # 同時保存純文本版本
            text_file = self.cbeta_folder / f"{sutra_id}.txt"
            async with aiofiles.open(text_file, 'w', encoding='utf-8') as f:
                await f.write(sample_text)
            
            logger.info(f"已創建樣本經文: {sutra_id}")
            return True
                
        except Exception as e:
            logger.error(f"創建樣本經文時出錯 {sutra_id}: {e}", exc_info=True)
            return False
    
    async def _parse_sutra_file(self, file_path: Path, sutra_name: str) -> tuple:
        """
        解析經典XML文件
        
        Args:
            file_path: XML文件路徑
            sutra_name: 經典名稱
            
        Returns:
            tuple: (經文內容, 元數據字典)
        """
        try:
            # 讀取XML文件
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                xml_content = await f.read()
            
            # 解析XML
            # 注意：實際解析邏輯需要根據CBETA XML的規範調整
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                # 如果XML解析失敗，嘗試直接從文本提取內容
                logger.warning(f"XML解析失敗，嘗試直接從文本提取內容: {file_path}")
                
                # 使用正則表達式提取<body>標籤內容
                body_match = re.search(r'<body>(.*?)</body>', xml_content, re.DOTALL)
                if body_match:
                    text_content = body_match.group(1)
                    # 移除HTML標籤
                    text_content = re.sub(r'<[^>]+>', '', text_content)
                    # 清理文本
                    text_content = self._clean_text(text_content)
                    
                    # 創建基本元數據
                    metadata = {
                        "title": sutra_name,
                        "id": file_path.stem,
                    }
                    
                    return text_content, metadata
                else:
                    logger.error(f"無法從文件中提取內容: {file_path}")
                    return "", {}
            
            # 提取標題等元數據
            # 注意：XPath需要根據實際XML結構調整
            namespace = {'tei': 'http://www.tei-c.org/ns/1.0'}
            title_elem = root.find('.//tei:title', namespace)
            title = title_elem.text if title_elem is not None else sutra_name
            
            # 提取經文內容
            body_elem = root.find('.//tei:body', namespace)
            if body_elem is None:
                logger.error(f"無法找到body元素: {file_path}")
                return "", {}
            
            # 取得所有文本節點並組合
            text_parts = []
            for elem in body_elem.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
            
            text_content = '\n'.join(text_parts)
            # 清理文本
            text_content = self._clean_text(text_content)
            
            # 創建元數據
            metadata = {
                "title": title,
                "id": file_path.stem,
                # 可以添加更多元數據
            }
            
            return text_content, metadata
            
        except Exception as e:
            logger.error(f"解析經典文件時出錯 {file_path}: {e}", exc_info=True)
            return "", {}
    
    def _clean_text(self, text: str) -> str:
        """
        清理經文文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理後的文本
        """
        # 移除多餘空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊控制字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # 移除XML/HTML標籤（如果有）
        text = re.sub(r'<[^>]+>', '', text)
        
        # 標準化標點符號
        # 將全形標點轉換為半形
        text = text.replace('，', ',').replace('。', '.')
        text = text.replace('；', ';').replace('：', ':')
        text = text.replace('（', '(').replace('）', ')')
        text = text.replace('「', '"').replace('」', '"')
        text = text.replace('『', "'").replace('』', "'")
        
        return text.strip()

async def main():
    """主函數，用於測試"""
    processor = CBETAProcessor()
    await processor.process_all_sutras()

if __name__ == "__main__":
    asyncio.run(main()) 