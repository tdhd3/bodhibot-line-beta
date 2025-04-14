# 使用官方 Python 鏡像作為基礎
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼和數據
COPY . .

# 確保數據目錄存在
RUN mkdir -p data/input data/output data/cbeta data/vector_db

# 設置環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 設置入口點
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]