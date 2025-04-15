# 佛教智慧對話系統測試指南

本文檔提供測試佛教智慧對話系統的詳細步驟和說明。

## 📋 測試類型

系統提供以下測試類型：

1. **基本功能測試** - 測試系統的核心功能是否正常工作
2. **LINE Bot 連接測試** - 測試與 LINE 平台的連接
3. **服務功能測試** - 測試回應生成和快速回覆等功能
4. **頻率限制測試** - 測試用戶頻率限制功能

## 🚀 運行測試

### 準備工作

1. 確保您已安裝所有依賴：
   ```bash
   pip install -r requirements.txt
   ```

2. 確保環境變數已正確設置（檢查 `.env` 文件）：
   - LINE_CHANNEL_SECRET
   - LINE_CHANNEL_ACCESS_TOKEN
   - OPENAI_API_KEY
   - 其他必要設定

3. 確保資料目錄結構已正確創建：
   ```
   data/
   ├── input/         # 用戶上傳文件
   ├── output/        # 處理結果輸出
   ├── cbeta/         # CBETA經文資料
   └── vector_db/     # 向量資料庫
   ```

### 運行自動化測試

#### 所有測試

運行所有測試：

```bash
python -m unittest discover tests
```

#### 單一測試檔案

運行特定測試：

```bash
# 基本功能測試
python -m unittest tests.test_basic

# LINE Bot 服務功能測試
python -m unittest tests.test_line_service

# 頻率限制測試
python -m unittest tests.test_rate_limit
```

#### 單一測試方法

運行特定測試方法：

```bash
python -m unittest tests.test_basic.TestBasicFunctionality.test_config
```

### 手動測試

#### 啟動應用程序

在一個終端窗口中啟動應用程序：

```bash
python -m app.main
```

#### LINE Bot 連接測試

在另一個終端窗口中運行 LINE Bot 連接測試：

```bash
python -m tests.test_line_bot
```

#### 手動 API 測試

使用 curl 或 Postman 測試 API 端點：

1. 健康檢查：
   ```bash
   curl http://localhost:8000/health
   ```

2. 根端點：
   ```bash
   curl http://localhost:8000/
   ```

3. 手動聊天：
   ```bash
   curl -X POST http://localhost:8000/api/line/chat \
   -H "Content-Type: application/json" \
   -d '{"user_id": "test_user_123", "message": "南無阿彌陀佛"}'
   ```

4. 新聞端點：
   ```bash
   curl http://localhost:8000/api/line/news
   ```

#### 使用 ngrok 進行 LINE Webhook 測試

1. 啟動 ngrok 將本地服務器暴露到互聯網：
   ```bash
   ngrok http 8000
   ```

2. 在 LINE Developers 控制台設置 Webhook URL：
   ```
   https://<your-ngrok-url>/api/line/webhook
   ```

3. 在 LINE 聊天中測試 Bot 回應

## 🧪 測試範例和預期結果

### 基本功能測試

- **配置測試**：檢查設定和配置是否正確加載
- **快速回覆管理器**：檢查是否能生成主選單、類別和上下文快速回覆
- **新聞處理器**：檢查是否能獲取和格式化新聞
- **CBETA 處理器**：檢查經文處理器初始化是否成功
- **用戶管理**：檢查敏感詞過濾、聊天歷史管理功能

### LINE Bot 服務功能測試

- **回應生成測試**：檢查是否能生成符合預期的回應
- **引用經文測試**：檢查是否能正確引用相關經文
- **快速回覆生成**：檢查是否根據上下文生成合適的建議問題

## 📊 測試報告解讀

測試結果將顯示成功 (.) 或失敗 (F) 的測試案例。例如：

```
.....F..
======================================================================
FAIL: test_news_processor (tests.test_basic.TestBasicFunctionality)
----------------------------------------------------------------------
...錯誤詳情...
```

- 通過的測試將顯示為 `.`
- 失敗的測試將顯示為 `F` 並附帶詳細錯誤信息

## 🔧 常見問題排除

1. **依賴問題**：確保已安裝所有必要的依賴庫
   ```bash
   pip install -r requirements.txt
   ```

2. **API 密鑰問題**：檢查 `.env` 文件中的 API 密鑰是否正確
   ```
   OPENAI_API_KEY=your_actual_openai_key
   LINE_CHANNEL_SECRET=your_actual_channel_secret
   LINE_CHANNEL_ACCESS_TOKEN=your_actual_access_token
   ```

3. **伺服器連接問題**：確保應用程序正在運行
   ```bash
   python -m app.main
   ```

4. **Redis 連接問題**：確保 Redis 服務運行中（如果使用）
   ```bash
   # 啟動 Redis 服務
   redis-server
   ```

5. **經文資料問題**：確保已下載必要的經文資料
   ```bash
   python scripts/download_cbeta.py --all
   ```

## 📝 提交測試報告

發現問題時，請提供以下信息：

1. 測試環境（操作系統、Python 版本）
2. 完整的錯誤信息
3. 重現步驟
4. 預期行為與實際行為的對比

這將幫助我們更快地解決問題並改進系統。 