# 佛教智慧對話系統

一個結合佛教唯識學與語意檢索的 LINE 智慧對話系統，能夠根據使用者語境提供適當的佛法指導。

## 📑 功能特點

- 🧠 **智能分析用戶認知層級與問題類型**：自動判斷用戶所處的認知階段和問題性質
- 🔄 **基於四攝法的對話策略**：根據用戶情況選擇布施、愛語、利行或同事策略
- 📚 **經典經文智能檢索與引用**：根據語意搜尋相關經文，提供有根據的回應
- 👤 **個性化的修行建議**：基於用戶問題和背景提供量身定制的修行建議
- 📱 **友善的用戶界面**：LINE聊天機器人提供簡便直觀的使用體驗
- 📰 **時事省思功能**：提供對當前新聞的佛教智慧觀點，每日更新三則熱門新聞並附帶省思
- 🧘 **正念冥想引導**：提供基於佛教傳統的冥想引導
- 🔄 **智能快速回覆**：根據對話內容智能推薦相關問題，提供便捷的後續互動選項
- 📝 **用戶回饋收集**：整合Google表單收集用戶滿意度和改進建議

## 🏗️ 系統架構

### 後端技術棧
- **語言處理主體**: [LangChain](https://www.langchain.com/) - 處理分類與檢索
- **對話節點流程**: [LangGraph](https://github.com/langchain-ai/langgraph) - 狀態遷移與互動分支
- **經典語義查詢**: [CBETA 經文](https://cbetaonline.dila.edu.tw/) + 向量資料庫 ([Chroma](https://docs.trychroma.com/))
- **使用者資料儲存**: [Redis](https://redis.io/) 或 [Firebase](https://firebase.google.com/) - 記錄認知與成長軌跡
- **API服務**: [FastAPI](https://fastapi.tiangolo.com/) - 提供 HTTP API
- **OpenAI模型**: [GPT-4o-mini](https://platform.openai.com/docs/models) - 提供高效能的NLP能力
- **新聞獲取**: [GNews API](https://gnews.io/) 及多個RSS備用源（中央社、Google News、ETToday等）
- **部署環境**: [Docker](https://www.docker.com/) + [Google Cloud Run](https://cloud.google.com/run)

### 前端界面
- **平台**: [LINE Messaging API](https://developers.line.biz/en/services/messaging-api/) - 用戶交互界面
- **交互元素**: Flex Message, Quick Reply, 圖片辨識
- **用戶界面**: 符合佛教美學的溫暖視覺設計

## 🚀 快速開始

### 前置條件

- [Python 3.8+](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/get-started) (可選，用於容器化部署)
- [LINE Developers 帳號](https://developers.line.biz/)
- [OpenAI API 金鑰](https://platform.openai.com/)
- [GNews API 金鑰](https://gnews.io/) (可選，用於新聞功能)

### 安裝步驟

1. **克隆專案**
   ```bash
   git clone https://github.com/yourusername/bodhibot-line-beta.git
   cd bodhibot-line-beta
   ```

2. **設置虛擬環境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. **安裝依賴套件**
   ```bash
   pip install -r requirements.txt
   ```

4. **設置環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 文件，填入所需的 API 金鑰和設定
   ```

5. **下載經文資料 (可選，但建議執行)**
   ```bash
   # 查看支持的經文列表
   python scripts/download_cbeta.py --list
   
   # 下載所有經文
   python scripts/download_cbeta.py --all
   
   # 下載特定經文，例如金剛經
   python scripts/download_cbeta.py --id T0235
   ```

6. **運行測試 (可選)**
   ```bash
   # 運行基本功能測試
   python -m unittest tests/test_basic.py
   ```

7. **啟動應用**
   ```bash
   python -m app.main
   ```

### Docker部署 (可選)

1. **建立 Docker 映像**
   ```bash
   docker build -t bodhibot-line-beta .
   ```

2. **運行容器**
   ```bash
   docker run -p 8000:8000 --env-file .env bodhibot-line-beta
   ```

### 在Google Cloud Run上部署

1. **建立 Docker 映像**
   ```bash
   docker build -t gcr.io/您的專案ID/bodhibot-line-beta .
   ```

2. **推送映像到 Google Container Registry**
   ```bash
   gcloud auth configure-docker
   docker push gcr.io/您的專案ID/bodhibot-line-beta
   ```

3. **部署到 Google Cloud Run**
   ```bash
   gcloud run deploy bodhibot --image gcr.io/您的專案ID/bodhibot-line-beta --platform managed --region asia-east1 --allow-unauthenticated --update-env-vars "LINE_CHANNEL_SECRET=您的密鑰,LINE_CHANNEL_ACCESS_TOKEN=您的令牌,OPENAI_API_KEY=您的OpenAI密鑰,GNEWS_API_KEY=您的GNews密鑰"
   ```

4. **使用返回的URL設定LINE Webhook**

## 📁 專案結構

```
bodhibot-line-beta/
├── app/                      # 應用程式主目錄
│   ├── api/                  # API 路由
│   │   └── routes/           # 路由處理器
│   │       └── line_webhook.py  # LINE webhook處理
│   ├── core/                 # 核心配置
│   │   └── config.py         # 全局設定
│   ├── data_processing/      # 資料處理
│   │   ├── file_processor.py   # 檔案處理
│   │   └── cbeta_processor.py  # CBETA經文處理
│   ├── models/               # 資料模型
│   ├── services/             # 服務
│   │   ├── sutra_retriever.py  # 經文檢索
│   │   ├── response_generator.py  # 回應生成
│   │   ├── quick_reply_manager.py  # 快速回覆管理
│   │   └── news_processor.py  # 新聞處理
│   └── main.py               # 主入口
├── data/                     # 資料目錄
│   ├── input/                # 輸入文件
│   ├── output/               # 輸出結果
│   ├── cbeta/                # CBETA經文
│   └── vector_db/            # 向量資料庫
├── scripts/                  # 腳本
│   └── download_cbeta.py     # 經文下載腳本
├── tests/                    # 測試
│   └── test_basic.py         # 基本功能測試
├── .env.example              # 環境變數範例
├── .gitignore                # Git忽略文件
├── Dockerfile                # Docker配置
├── requirements.txt          # Python依賴
└── README.md                 # 說明文件
```

## 📖 使用指南

### LINE Bot 設置

1. 前往 [LINE Developers](https://developers.line.biz/) 創建一個新的 Provider 和 Channel
2. 在 Channel 設定中獲取 Channel secret 和 Channel access token
3. 設置 Webhook URL 為 `https://您的網域/api/line/webhook`
4. 開啟 "Use webhook" 選項
5. 將 Channel secret 和 Channel access token 添加到 `.env` 文件

### 添加自定義文檔

1. 將 `.txt` 或 `.pdf` 文件放入 `data/input` 目錄
2. 系統將自動處理和向量化這些文件
3. 處理完成後，文件的內容將可用於回應生成

### CBETA 經文處理

1. 使用提供的下載腳本獲取經文:
   ```bash
   # 下載所有支持的經文
   python scripts/download_cbeta.py --all
   
   # 檢視可用經文列表
   python scripts/download_cbeta.py --list
   ```
2. 或通過API端點手動觸發處理:
   ```bash
   curl -X GET http://localhost:8000/process-cbeta
   ```

### 快速回覆管理

快速回覆功能通過 `QuickReplyManager` 類實現，提供三種主要的回覆類型：

1. **主選單快速回覆**：顯示主要功能類別，如佛法學習、生活應用等
2. **類別快速回覆**：根據用戶選擇顯示該類別的常見問題
3. **上下文智能快速回覆**：根據當前對話內容自動推薦相關問題

系統會通過關鍵詞映射分析用戶輸入，確定最相關的類別，並提供適合的後續提問建議。

### 用戶回饋功能

系統整合了Google表單收集用戶反饋：

1. **快速鍵連結**：每個對話介面都有「📝 用戶回饋」按鈕，點擊直接跳轉至表單
2. **系統選單**：「系統功能」中也有「提供使用回饋」選項
3. **回饋表單**：收集整體使用體驗、準確性、對話速度和易用性評分，以及功能建議和問題反饋

### 新聞功能配置

新聞功能透過 `NewsProcessor` 類實現：

1. **新聞來源**：優先使用 GNews API，如未設置或請求失敗會自動降級使用台灣中央社RSS、Google News、ETToday等備用源
2. **新聞更新頻率**：可在 `.env` 中設置 `NEWS_UPDATE_INTERVAL`，默認為3600秒（1小時）
3. **觀點生成**：使用 OpenAI 模型為每條新聞生成佛教觀點，保持中立性和啟發性

### 主要功能

1. **佛法問答**：直接提問佛法相關問題，系統自動分析認知層級並提供適合回應
2. **時事省思**：獲取最新新聞並附加佛教視角的觀點解讀，每日自動更新
3. **禪修引導**：提供簡易的禪修冥想指導
4. **智能快速回覆**：根據對話內容提供相關問題建議，最多支持13個快速回覆選項
5. **用戶回饋**：提供直接的回饋管道，幫助持續改進系統

## 🧪 認知層級與四攝法

### 認知層級
1. **第一層（基礎認知層）**：對佛法知識缺乏，思維方式較為世俗
2. **第二層（進階探索層）**：初步接觸佛法，了解基本概念
3. **第三層（深度理解層）**：系統性學習佛法，理解較深的佛法概念
4. **第四層（修行實踐層）**：深厚佛法基礎，關注修行實踐和證悟

### 四攝法策略
1. **布施（Dana）**：通過給予幫助建立關係，精神或物質上的給予
2. **愛語（Priyavacana）**：溫和親切的言語，增進理解和接受
3. **利行（Arthakrtya）**：實際行動幫助他人，指導正確道路
4. **同事（Samanarthata）**：融入他人處境，以平等態度交往

## 🤖 交互範例

### 基本問答
```
用戶: 我最近壓力很大，怎麼辦？
機器人: [根據認知層級和問題類型生成回應，並引用相關經文]
```

### 冥想引導
```
用戶: 請引導我進行靜心冥想
機器人: [提供基於佛教傳統的冥想指導]
```

### 經文探索
```
用戶: 六祖壇經中有哪些重要教義？
機器人: [分析六祖壇經的核心教義，並引用相關段落]
```

### 時事省思
```
用戶: 時事省思
機器人: [提供今日最新新聞及佛法視角的觀點]
```

### 使用快速回覆
```
用戶: 主選單
機器人: 您好，請選擇您想了解的主題：
[顯示主選單快速回覆按鈕]

用戶: [點擊生活應用按鈕]
機器人: 關於「生活應用」，您可以問以下問題：
[顯示生活應用類別相關的問題建議]
```

### 提供回饋
```
用戶: [點擊「📝 用戶回饋」按鈕]
系統: [跳轉至Google表單]

或

用戶: 提供使用回饋
機器人: 感謝您的使用！您可以通過以下連結提供寶貴意見：
[顯示回饋表單連結]
```

## 🔄 開發路線圖

- [x] **第一階段**：基礎LINE機器人框架、CBETA資料處理與向量化、簡單回應生成
- [x] **第二階段**：用戶認知層級分類、四攝法對話策略、經文引用系統、快速回覆、新聞功能
- [x] **第三階段**：用戶回饋機制、模型升級至GPT-4o-mini、測試腳本、經文下載工具
- [ ] **第四階段**：用戶狀態管理、學習進度追蹤、UI/UX優化、多樣化的禪修引導
- [ ] **第五階段**：圖像識別整合、社區功能、進階數據分析、個人化修行計劃

## 📊 評估與改進

- **用戶滿意度調查**：通過整合的回饋表單定期收集用戶反饋
- **對話品質評估**：根據回應相關性和幫助性評估
- **用戶成長追蹤**：分析用戶認知層級的變化和進展
- **快速回覆點擊率分析**：評估推薦問題的相關性和有用性
- **性能監控**：追蹤模型響應時間和資源使用情況

## 📝 使用技巧

- **開始對話**：輸入「主選單」隨時返回主功能選單
- **清除歷史**：輸入「清除對話記錄」重置對話
- **引導冥想**：輸入「禪修引導」獲取靜心指導
- **獲取說明**：輸入「查看使用說明」了解系統功能
- **探索新聞**：輸入「時事省思」獲取新聞及佛法觀點
- **深入探索**：點擊快速回覆按鈕深入探索特定主題
- **提供反饋**：使用快速鍵「📝 用戶回饋」分享您的使用體驗

## 📜 授權協議

本專案採用 [MIT 授權協議](LICENSE)。

## 👥 參與貢獻

歡迎貢獻！請閱讀 [貢獻指南](CONTRIBUTING.md) 了解如何參與。

## 🙏 致謝

- [CBETA 中華電子佛典協會](https://www.cbeta.org/) 提供數位佛典資源
- [OpenAI](https://openai.com/) 提供 GPT 模型
- [LINE Developers](https://developers.line.biz/) 提供訊息 API
- [GNews](https://gnews.io/) 提供新聞API
- 所有專案貢獻者

## 📞 聯絡方式

如有任何問題或建議，請聯絡 [your.email@example.com](mailto:your.email@example.com) 