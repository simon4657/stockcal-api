#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本
每日自動生成熱點、策略和事件資料
方案 B：完全動態生成未來 7-30 天的重要事件
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
        contents=prompt
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
        contents=prompt
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
    """使用 Gemini 生成未來 7-30 天的重要事件"""
    
    # 計算日期範圍
    today = datetime.now()
    start_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    
    prompt = f"""你是一位專業的台股分析師。請根據今天 ({TODAY}) 的市場狀況，預測未來 7-30 天內（{start_date} 到 {end_date}）可能發生的重要事件。

請以 JSON 格式輸出 8-12 個事件，包含以下欄位：
- id: 唯一識別碼 (格式: MM-DD-關鍵字，例如: 11-25-nvidia)
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
    "id": "11-25-nvidia",
    "date": "2025-11-25",
    "title": "輝達 Q3 財報公布",
    "market": "US",
    "type": "corporate",
    "trend": "bull",
    "relatedStocks": ["廣達 (2382)", "緯創 (3231)", "技嘉 (2376)", "華碩 (2357)"],
    "description": "輝達 Q3 財報將公布，市場關注 AI 晶片需求與 Blackwell 架構進展。若營收優於預期，台系供應鏈將受惠。",
    "strategy": "若財報優於預期，隔日開盤可追價廣達、緯創等 AI 伺服器股。設定停損於 5 日線下。"
  }},
  {{
    "id": "12-10-fomc",
    "date": "2025-12-10",
    "title": "美國 CPI 與 FOMC 會議",
    "market": "US",
    "type": "critical",
    "trend": "neutral",
    "relatedStocks": ["台積電 (2330)", "聯發科 (2454)", "中華電 (2412)", "富邦金 (2881)"],
    "description": "美國 11 月 CPI 數據公布，FOMC 將決定利率政策。通膨數據與升息展望將影響全球股市資金流向。",
    "strategy": "會議前減碼高風險個股，保留現金。若降息訊號明確，可逢低布局科技股；若鷹派則觀望。"
  }}
]

請根據以下資訊生成事件：
1. **重要財報發布**：美股科技巨頭（NVIDIA、AMD、TSMC ADR、Dell、HP、Broadcom 等）
2. **經濟數據公布**：美國 CPI、PPI、非農就業、消費者信心指數、PMI 等
3. **央行會議**：Fed FOMC、台灣央行理監事會議
4. **產業重要事件**：AI 新品發表、半導體展會、電動車發表會
5. **台股重要事件**：台積電法說會、聯發科法說會、重要除權息日
6. **政策變動**：台灣產業政策、美國晶片法案、貿易政策

**注意事項**：
- 日期必須真實合理（例如 FOMC 通常在月中，財報季在每季末）
- 事件必須具體且可能發生
- 相關個股必須真實存在
- 涵蓋不同類型的事件（財報、數據、政策、產業）
- 按日期由近到遠排序

只輸出 JSON 陣列，不要其他說明文字。"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt
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
        print(f"[{datetime.now()}] 開始自動更新資料...")
        
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
        
        # 生成未來事件
        print("正在生成未來 7-30 天的重要事件...")
        events = generate_future_events(client)
        with open('data_events.json', 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"✓ 事件資料已更新 ({len(events)} 項)")
        
        # 顯示事件摘要
        print("\n事件摘要：")
        for event in events[:5]:  # 只顯示前 5 個
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
