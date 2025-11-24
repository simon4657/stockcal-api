# StockCal API

> 提供 StockCal 應用程式的後端 API 服務

## 📋 API 端點

### 1. 獲取月度事件
```
GET /api/events
```
返回當月及未來兩個月的重要股市事件。

**更新頻率**: 每月更新

### 2. 獲取每日熱點
```
GET /api/hot-trends
```
返回當日的熱門族群和個股。

**更新頻率**: 每日更新

### 3. 獲取每日策略
```
GET /api/strategies
```
返回當日的操作策略建議。

**更新頻率**: 每日更新

### 4. 健康檢查
```
GET /health
```
檢查 API 服務狀態。

## 🔧 本地開發

### 安裝依賴
```bash
pip install -r requirements.txt
```

### 啟動服務
```bash
python main.py
```

服務會在 `http://localhost:8000` 啟動。

### 查看 API 文件
訪問 `http://localhost:8000/docs` 查看自動生成的 Swagger 文件。

## 📝 資料更新

### 更新月度事件
編輯 `data_events.json` 檔案，添加或修改事件資料。

### 更新每日熱點
編輯 `data_hot_trends.json` 檔案，更新熱門族群資訊。

### 更新每日策略
編輯 `data_strategies.json` 檔案，更新操作策略建議。

## 🚀 部署到 Render

1. 推送程式碼到 GitHub
2. 在 Render Dashboard 中建立新的 Web Service
3. 連接 GitHub 儲存庫
4. Render 會自動讀取 `render.yaml` 配置並部署

## 📦 技術棧

- **框架**: FastAPI
- **Python 版本**: 3.11+
- **部署平台**: Render

## 🔒 CORS 設定

目前允許所有來源的跨域請求。生產環境建議限制為特定網域：

```python
allow_origins=["https://your-frontend-domain.com"]
```

## 📄 授權

MIT License
