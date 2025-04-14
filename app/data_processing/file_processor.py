import os
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

import aiofiles
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from app.core.config import settings

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileProcessor:
    """
    處理各種檔案類型（TXT、PDF）的類別。
    負責讀取、清理、分割文本，並將其存入向量資料庫。
    """
    
    def __init__(self):
        """初始化檔案處理器"""
        self.input_folder = Path(settings.INPUT_FOLDER)
        self.output_folder = Path(settings.OUTPUT_FOLDER)
        self.vector_db_path = Path(settings.VECTOR_DB_PATH)
        
        # 創建必要的目錄
        self.input_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # 準備嵌入模型
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL
        )
        
        # 準備文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
    
    async def process_file(self, file_path: Path) -> bool:
        """
        處理單一檔案
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            bool: 處理成功返回True，否則返回False
        """
        try:
            logger.info(f"開始處理檔案: {file_path}")
            
            # 檢查檔案是否存在
            if not file_path.exists():
                logger.error(f"檔案不存在: {file_path}")
                return False
            
            # 根據檔案類型選擇讀取方法
            file_extension = file_path.suffix.lower()
            if file_extension == '.txt':
                text = await self._read_text_file(file_path)
            elif file_extension == '.pdf':
                text = await self._read_pdf_file(file_path)
            else:
                logger.error(f"不支援的檔案類型: {file_extension}")
                return False
            
            if not text:
                logger.error(f"無法從檔案中讀取文本: {file_path}")
                return False
            
            # 清理文本
            cleaned_text = self._clean_text(text)
            
            # 分割文本
            chunks = self.text_splitter.split_text(cleaned_text)
            logger.info(f"文件被分割為 {len(chunks)} 個片段")
            
            # 準備元數據
            metadata_list = []
            for i, _ in enumerate(chunks):
                metadata_list.append({
                    "source": file_path.name,
                    "chunk_id": i,
                    "file_type": file_extension[1:],  # 移除開頭的點
                    "custom_document": True,
                })
            
            # 將文本存入向量資料庫
            collection_name = "custom_documents"
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.vector_db_path)
            )
            
            # 添加文檔到向量存儲
            vectorstore.add_texts(chunks, metadata_list)
            vectorstore.persist()
            
            logger.info(f"成功處理並存儲檔案: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"處理檔案時出錯: {e}", exc_info=True)
            return False
    
    async def _read_text_file(self, file_path: Path) -> str:
        """
        讀取文字檔案內容
        
        Args:
            file_path: 文件路徑
            
        Returns:
            str: 檔案內容
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            return content
        except UnicodeDecodeError:
            # 如果utf-8解碼失敗，嘗試其他編碼
            encodings = ['big5', 'gb18030', 'latin-1']
            for encoding in encodings:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as file:
                        content = await file.read()
                    logger.info(f"使用 {encoding} 編碼讀取檔案成功")
                    return content
                except UnicodeDecodeError:
                    continue
            
            logger.error(f"無法用常見編碼讀取檔案: {file_path}")
            return ""
    
    async def _read_pdf_file(self, file_path: Path) -> str:
        """
        讀取PDF檔案內容
        
        Args:
            file_path: PDF檔案路徑
            
        Returns:
            str: PDF檔案內容
        """
        try:
            # 使用 pypdf 讀取PDF 
            # 注意: pypdf 是同步的，但我們將它包在異步函數中
            reader = PdfReader(file_path)
            text = ""
            
            # 讀取所有頁面內容
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            logger.error(f"讀取PDF檔案時出錯: {e}", exc_info=True)
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本內容，移除無用的字符並標準化格式
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理後的文本
        """
        # 移除多餘空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊控制字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # 標準化標點符號（可選，視情況調整）
        
        return text.strip()
    
    async def watch_folder(self):
        """
        監視輸入資料夾的變化，處理新增的文件
        
        注意：此方法是使用輪詢方式實現的簡易監視，在生產環境中應考慮使用 watchdog 等
        """
        processed_files = set()
        
        while True:
            try:
                # 獲取目錄中所有文件
                files = [f for f in self.input_folder.glob('*') if f.is_file() and 
                         f.suffix.lower() in ('.txt', '.pdf')]
                
                # 處理新文件
                for file_path in files:
                    if file_path not in processed_files:
                        success = await self.process_file(file_path)
                        if success:
                            processed_files.add(file_path)
                            # 可選：移動已處理的文件到輸出目錄
                            # dst = self.output_folder / file_path.name
                            # file_path.rename(dst)
                
                # 等待一段時間再檢查
                await asyncio.sleep(10)  # 每10秒檢查一次
                
            except Exception as e:
                logger.error(f"監視資料夾時出錯: {e}", exc_info=True)
                await asyncio.sleep(30)  # 發生錯誤時，等待更長時間再重試

async def main():
    """主函數，用於測試"""
    processor = FileProcessor()
    await processor.watch_folder()

if __name__ == "__main__":
    asyncio.run(main()) 