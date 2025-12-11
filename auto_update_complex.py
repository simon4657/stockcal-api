#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本 v2
每日自動生成熱點、策略和事件資料
改進：使用 Google Search Grounding 確保事件日期準確
"""
import json
import os
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 配置
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TODAY = datetime.now().strftime('%Y-%m-%d')

def init_gemini():
    """初始化 Gemini 客戶端"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    return client

def generate_hot_trends(client):
    """使用 Gemini 生成每日熱點"""
    
    prompt = f"""你是一位專業的台股分析師。請根據今天 ({TODAY}) 的市場狀況，生成 4 個最熱門的族群或主題。

請以 JSON 格式輸出，包含以下欄位：
- id: 唯一識別碼 (格式: hot-1, hot-2...)
- name: 族群名稱
- strength: 資金強度 (0-100)
- trend: 趨勢 (up/down/neutral/volatile)
- stocks: 相關個股列表 (3-5 檔，格式: "股票名稱 (代碼)")
- reason: 熱點原因說明 (50字內)
- updatedAt: 更新日期 ({TODAY})

範例格式：
[
  {{
    "id": "hot-1",
    "name": "AI 伺服器",
    "strength": 90,
    "trend": "up",
    "stocks": ["廣達 (2382)", "緯創 (3231)", "英業達 (2356)"],
    "reason": "輝達新品發表會帶動供應鏈訂單湧入",
    "updatedAt": "{TODAY}"
  }}
]

請根據以下資訊生成：
1. 近期台股市場熱點
2. 外資買超族群
3. 主力資金流向
4. 產業趨勢

只輸出 JSON，不要其他說明文字。"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        )
    )
    
    # 提取 JSON
    text = response.text.strip()
    # 移除可能的 markdown 標記
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    return json.loads(text.strip())

def generate_strategies(client):
    """使用 Gemini 生成每日策略"""
    
    prompt = f"""你是一位專業的台股操盤手。請根據今天 ({TODAY}) 的市場狀況，生成 3 個操作策略建議。

請以 JSON 格式輸出，包含以下欄位：
- id: 唯一識別碼 (格式: st-1, st-2...)
- title: 策略標題
- type: 策略類型 (bull/bear/neutral/volatile)
- desc: 策略描述 (80字內)
- risk: 風險等級 (低/中/高)
- target: 關注目標
- updatedAt: 更新日期 ({TODAY})

範例格式：
[
  {{
    "id": "st-1",
    "title": "AI 族群短線操作",
    "type": "bull",
    "desc": "AI 伺服器族群持續強勢，建議沿 5 日線操作，不破線續抱。",
    "risk": "中",
    "target": "AI 伺服器股",
    "updatedAt": "{TODAY}"
  }}
]

請根據以下資訊生成：
1. 大盤趨勢判斷
2. 強勢族群操作建議
3. 風險控管提醒

只輸出 JSON，不要其他說明文字。"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        )
    )
    
    # 提取 JSON
    text = response.text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    return json.loads(text.strip())

def generate_future_events(client):
    """使用 Gemini 生成當月（N）和下個月（N+1）的重要事件，使用 Google Search 確保日期準確"""
    
    # 計算日期範圍：當月第一天到下個月最後一天
    today = datetime.now()
    
    # 當月第一天
    current_month_start = today.replace(day=1)
    
    # 下個月第一天
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)
    
    # 下下個月第一天（用來計算下個月最後一天）
    if next_month_start.month == 12:
        next_next_month_start = next_month_start.replace(year=next_month_start.year + 1, month=1, day=1)
    else:
        next_next_month_start = next_month_start.replace(month=next_month_start.month + 1, day=1)
    
    # 下個月最後一天
    next_month_end = next_next_month_start - timedelta(days=1)
    
    start_date = current_month_start.strftime('%Y-%m-%d')
    end_date = next_month_end.strftime('%Y-%m-%d')
    current_month_name = today.strftime('%Y年%m月')
    next_month_name = next_month_start.strftime('%Y年%m月')
    
    prompt = f"""你是一位專業的台股分析師。請搜尋並預測 {current_month_name} 和 {next_month_name} 兩個月（{start_date} 到 {end_date}）可能發生的重要事件。

**重要提醒**：
1. **必須生成 25-30 個事件**，這是強制要求，不可少於 25 個
2. 對於重要事件（FOMC、權值股法說會），請使用 Google Search 搜尋確認日期
3. 對於無法確認日期的事件，可以根據歷史規律估計，但仍須包含在輸出中
4. 台灣事件必須佔 50% 以上
5. 事件類型要多樣化，涵蓋法說會、政府政策、經濟數據、產業事件等

請以 JSON 格式輸出 25-30 個事件，包含以下欄位：
- id: 唯一識別碼 (格式: MMDD-關鍵字，例如: 1225-tsmc)
- date: 事件日期 (YYYY-MM-DD，必須在 {start_date} 到 {end_date} 之間)
- title: 事件標題 (簡短有力，15字內)
- market: 市場 (TW/US/CN/Global)
- type: 事件類型 (hot=熱點事件, corporate=財報法說, critical=重大數據)
- trend: 預期趨勢 (bull=偏多, bear=偏空, neutral=中性)
- relatedStocks: 相關個股列表 (3-5 檔，格式: "股票名稱 (代碼)")
- description: 事件描述與重點 (80字內)
- strategy: 操作策略建議 (80字內)

範例格式：
[
  {{
    "id": "0116-tsmc",
    "date": "2026-01-16",
    "title": "台積電法說會",
    "market": "TW",
    "type": "corporate",
    "trend": "bull",
    "relatedStocks": ["台積電 (2330)", "聯發科 (2454)", "弘塑 (3131)", "家登 (3680)"],
    "description": "台積電召開法人說明會，公布 Q4 2025 財報與 2026 年展望。市場關注先進製程進度、資本支出與 AI 晶片需求。",
    "strategy": "法說前可提前布局，若展望優於預期，設備供應鏈將受惠。注意法說後外資動向。"
  }}
]

請搜尋並包含以下類型的事件（每類至少 2-3 個）：

### 台灣重要事件（必須包含 15-20 個，請搜尋確認日期）：
1. **權值股法說會**（至少 8 個）：
   - 台積電 (2330)、聯發科 (2454)、鴻海 (2317)、台達電 (2308)
   - 日月光投控 (3711)、大立光 (3008)、聯電 (2303)、廣達 (2382)
   - 緯創 (3231)、和碩 (4938)、可成 (2474)、國巨 (2327)

2. **政府政策與會議**（至少 3 個）：
   - 行政院產業政策說明
   - 立法院重要法案審查（產創條例、電業法、AI 發展條例等）
   - 經濟部產業補助公告
   - 國發會經濟展望報告
   - 金管會金融政策說明

3. **央行與金融**（至少 2 個）：
   - 台灣央行理監事會議（利率決策）
   - 金管會保險業監理會議
   - 證交所重大宣布

4. **經濟數據**（至少 4 個）：
   - 台灣 GDP 成長率公布
   - 外銷訂單統計
   - PMI 指數公布
   - 消費者物價指數 (CPI)
   - 失業率統計
   - 工業生產指數

5. **產業重要事件**（至少 2 個）：
   - 台北國際電腦展相關活動
   - 半導體展覽
   - 電動車產業論壇
   - 綠能產業展覽

6. **除權息旺季**（至少 1 個）：
   - 重要個股除權息日（台積電、鴻海、聯發科等）

### 美國重要事件（包含 8-10 個，請搜尋確認日期）：
1. **科技巨頭財報**（至少 5 個）：
   - NVIDIA、AMD、Intel、Qualcomm
   - Apple、Microsoft、Google、Amazon、Meta
   - Dell、HP、Broadcom、Cisco

2. **經濟數據**（至少 3 個）：
   - CPI 消費者物價指數
   - PPI 生產者物價指數
   - 非農就業數據
   - 消費者信心指數
   - PMI 指數
   - 零售銷售數據

3. **Fed FOMC 會議**：請搜尋確認日期

4. **產業事件**（至少 1 個）：
   - AI 新品發表會
   - CES 消費電子展
   - 半導體產業峰會

**注意事項**：
- **最重要：必須生成 25-30 個事件，不可少於 25 個！**
- 對於 FOMC 會議、台積電、聯發科、鴻海等權值股法說會，必須使用 Google Search 搜尋確認日期
- 其他事件可以根據歷史規律估計日期（例如 PMI 通常月初公布、CPI 通常月中公布）
- 台灣事件必須佔 50% 以上（即 15-20 個）
- 美國事件 8-10 個
- 確保每個類型都有足夠的事件：法說會、政策、數據、產業
- 按日期由近到遠排序

**再次強調：必須輸出完整的 25-30 個事件，不要因為無法確認日期而減少數量！**

只輸出 JSON 陣列，不要其他說明文字。"""

    # 使用 Google Search Grounding
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,  # 降低溫度以提高準確性
            tools=[types.Tool(google_search=types.GoogleSearch())],  # 啟用 Google Search
        )
    )
    
    # 提取 JSON
    text = response.text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    events = json.loads(text.strip())
    
    # 過濾並排序事件
    today_dt = datetime.now()
    valid_events = []
    
    for event in events:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            # 只保留未來的事件
            if event_date > today_dt:
                valid_events.append(event)
        except:
            continue
    
    # 按日期排序
    valid_events.sort(key=lambda x: x['date'])
    
    return valid_events

def update_data_files():
    """更新資料檔案"""
    try:
        print(f"[{datetime.now()}] 開始自動更新資料（使用 Google Search Grounding）...")
        
        # 初始化 Gemini
        client = init_gemini()
        print("✓ Gemini 客戶端初始化成功")
        
        # 生成熱點資料
        print("正在生成每日熱點...")
        hot_trends = generate_hot_trends(client)
        with open('data_hot_trends.json', 'w', encoding='utf-8') as f:
            json.dump(hot_trends, f, ensure_ascii=False, indent=2)
        print(f"✓ 熱點資料已更新 ({len(hot_trends)} 項)")
        
        # 生成策略資料
        print("正在生成每日策略...")
        strategies = generate_strategies(client)
        with open('data_strategies.json', 'w', encoding='utf-8') as f:
            json.dump(strategies, f, ensure_ascii=False, indent=2)
        print(f"✓ 策略資料已更新 ({len(strategies)} 項)")
        
        # 生成未來事件（使用 Google Search）
        print("正在生成當月和下個月的重要事件（使用 Google Search 確認日期）...")
        events = generate_future_events(client)
        with open('data_events.json', 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"✓ 事件資料已更新 ({len(events)} 項)")
        
        # 顯示事件摘要
        print("\n事件摘要：")
        tw_count = sum(1 for e in events if e['market'] == 'TW')
        us_count = sum(1 for e in events if e['market'] == 'US')
        print(f"  台灣事件: {tw_count} 個")
        print(f"  美國事件: {us_count} 個")
        print(f"  其他事件: {len(events) - tw_count - us_count} 個")
        print("\n前 5 個事件：")
        for event in events[:5]:
            print(f"  - {event['date']}: {event['title']} ({event['market']})")
        if len(events) > 5:
            print(f"  ... 還有 {len(events) - 5} 個事件")
        
        print(f"\n[{datetime.now()}] 資料更新完成！")
        return True
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_data_files()
    exit(0 if success else 1)
