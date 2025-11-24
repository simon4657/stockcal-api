# StockCal 自動更新設定指南

> 如何啟用每日自動更新功能

## 🤖 功能說明

自動更新系統會：
- ✅ **每天早上 8:00 AM** 自動執行
- ✅ 使用 **Gemini AI** 分析市場狀況
- ✅ 自動生成**每日熱點**和**每日策略**
- ✅ 自動更新 JSON 檔案並推送到 GitHub
- ✅ 觸發 Render 自動部署

---

## 📋 設定步驟

### 步驟 1：取得 Gemini API Key

1. 前往 https://ai.google.dev
2. 登入 Google 帳號
3. 點擊「Get API Key」
4. 建立新的 API Key 或使用現有的
5. 複製 API Key

### 步驟 2：在 GitHub 設定 Secret

1. 前往 GitHub 儲存庫
   - https://github.com/simon4657/stockcal-api

2. 點擊 **「Settings」** → **「Secrets and variables」** → **「Actions」**

3. 點擊 **「New repository secret」**

4. 添加 Secret：
   - **Name**: `GEMINI_API_KEY`
   - **Value**: 您的 Gemini API Key

5. 點擊 **「Add secret」**

### 步驟 3：啟用 GitHub Actions

1. 在儲存庫中，點擊 **「Actions」** 標籤

2. 如果看到「Workflows aren't being run on this repository」
   - 點擊 **「I understand my workflows, go ahead and enable them」**

3. 找到 **「Auto Update Stock Data」** 工作流程

4. 點擊 **「Enable workflow」**

### 步驟 4：測試自動更新

1. 在 **「Actions」** 頁面中
2. 選擇 **「Auto Update Stock Data」**
3. 點擊右側的 **「Run workflow」** 按鈕
4. 選擇 `master` 分支
5. 點擊 **「Run workflow」**

6. 等待執行完成（約 30 秒）
7. 檢查是否有新的 commit（標題為 "Auto update: YYYY-MM-DD HH:MM:SS"）

---

## 🕐 執行時間

### 自動執行
- **時間**: 每天早上 **8:00 AM (台北時間)**
- **頻率**: 每日一次
- **觸發**: GitHub Actions Cron Job

### 手動執行
您也可以隨時手動觸發更新：
1. 前往 **「Actions」** → **「Auto Update Stock Data」**
2. 點擊 **「Run workflow」**

---

## 📊 更新流程

```
08:00 AM
   │
   ▼
┌─────────────────────┐
│ GitHub Actions 啟動  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 執行 auto_update.py │
│ - 呼叫 Gemini AI    │
│ - 分析市場狀況      │
│ - 生成熱點和策略    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 更新 JSON 檔案      │
│ - data_hot_trends   │
│ - data_strategies   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 推送到 GitHub       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Render 自動部署     │
│ (約 1-2 分鐘)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 前端自動獲取新資料   │
└─────────────────────┘
```

---

## 🔍 監控與驗證

### 檢查執行狀態

1. **GitHub Actions**
   - 前往 **「Actions」** 標籤
   - 查看最新的執行記錄
   - ✅ 綠色勾勾 = 成功
   - ❌ 紅色叉叉 = 失敗

2. **查看 Commit 歷史**
   - 前往儲存庫首頁
   - 查看是否有新的 "Auto update" commit

3. **驗證 API 資料**
   - 訪問 https://stockcal-api.onrender.com/api/hot-trends
   - 檢查 `updatedAt` 欄位是否為今天的日期

### 檢查前端顯示

1. 開啟 StockCal 應用程式
2. 前往「熱點」和「策略」分頁
3. 確認資料已更新

---

## ⚙️ 自訂設定

### 修改執行時間

編輯 `.github/workflows/auto-update.yml`：

```yaml
on:
  schedule:
    # 修改這行的 cron 表達式
    - cron: '0 0 * * *'  # 目前是 8:00 AM (UTC+8)
```

**Cron 表達式說明：**
- `0 0 * * *` = 每天 8:00 AM (台北時間)
- `0 1 * * *` = 每天 9:00 AM (台北時間)
- `0 23 * * *` = 每天 7:00 AM (台北時間)

### 修改 AI 提示詞

編輯 `auto_update.py` 中的 `prompt` 變數，調整 AI 生成的內容風格和重點。

---

## 🚨 故障排除

### 問題 1：GitHub Actions 執行失敗

**可能原因：**
- GEMINI_API_KEY 未設定或錯誤
- API 配額用盡
- 網路連線問題

**解決方法：**
1. 檢查 GitHub Secrets 中的 API Key 是否正確
2. 查看 Actions 執行日誌中的錯誤訊息
3. 手動執行測試

### 問題 2：資料未更新

**可能原因：**
- GitHub Actions 未啟用
- Cron 時間設定錯誤
- Git push 權限問題

**解決方法：**
1. 確認 Actions 已啟用
2. 手動觸發測試
3. 檢查儲存庫權限設定

### 問題 3：AI 生成的內容不符預期

**解決方法：**
1. 修改 `auto_update.py` 中的 prompt
2. 調整 AI 模型參數
3. 手動編輯 JSON 檔案作為備份

---

## 💰 成本估算

### GitHub Actions
- ✅ **免費**：公開儲存庫無限制
- ✅ 每月 2000 分鐘免費額度（私有儲存庫）

### Gemini API
- ✅ **免費額度**：每天 1500 次請求
- ✅ 本系統每天使用約 2 次請求（熱點 + 策略）
- ✅ 完全在免費額度內

---

## 📚 相關文件

- **GitHub Actions 文件**: https://docs.github.com/en/actions
- **Gemini API 文件**: https://ai.google.dev/docs
- **Cron 表達式產生器**: https://crontab.guru/

---

## ✅ 設定完成檢查清單

- [ ] 已取得 Gemini API Key
- [ ] 已在 GitHub 設定 GEMINI_API_KEY Secret
- [ ] 已啟用 GitHub Actions
- [ ] 已手動測試執行一次
- [ ] 已確認資料成功更新
- [ ] 已驗證前端顯示正確

---

完成以上設定後，您的 StockCal 就會每天自動更新資料，無需手動維護！
