# 菩薩小老師 - 依賴管理指南

## 依賴文件說明

本專案包含兩個依賴管理文件：

1. `requirements.txt` - 包含主要直接依賴的固定版本
2. `requirements-lock.txt` - 包含所有依賴（直接和間接）的完整固定版本清單

## 安裝依賴

### 基本安裝（僅主要依賴）

```bash
pip install -r requirements.txt
```

### 完全鎖定安裝（推薦用於生產環境）

```bash
pip install -r requirements-lock.txt
```

## 依賴更新流程

為確保系統穩定性，請遵循以下依賴更新流程：

1. 在測試環境中測試新版本依賴
2. 更新 `requirements.txt` 中的特定依賴版本
3. 安裝更新後的依賴並測試應用程式
4. 使用 `pip freeze > requirements-lock.txt` 生成新的完整依賴鎖定文件
5. 提交兩個文件到版本控制系統

## 安全更新

當依賴庫發布安全更新時，請優先更新這些庫：

```bash
# 查看可能需要安全更新的依賴庫
pip list --outdated

# 更新特定依賴庫到最新版本
pip install --upgrade 依賴庫名稱==x.y.z

# 更新依賴鎖定文件
pip freeze > requirements-lock.txt
```

## 依賴管理最佳實踐

1. **始終使用固定版本** - 避免使用 `>=` 或 `~=` 等浮動版本限制符
2. **定期更新依賴** - 每月或每季檢查一次依賴更新，特別是安全相關更新
3. **分階段測試** - 先在開發環境測試更新，再在測試環境確認，最後部署到生產環境
4. **記錄變更** - 維護依賴更新日誌，記錄每次更新的原因和影響

透過嚴格管理依賴版本，可以確保應用程式在不同環境中表現一致，減少因依賴更新導致的系統不穩定或意外錯誤。 