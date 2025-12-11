#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本 v3
簡化 prompt，提高穩定性
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
    """使用 Gemini 生成當月和下個月的重要事件（簡化版）"""
    
    # 計算日期範圍
    today = datetime.now()
    current_month_start = today.replace(day=1)
    
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)
    
    if next_month_start.month == 12:
        next_next_month_start = next_month_start.replace(year=next_month_start.year + 1, month=1, day=1)
    else:
        next_next_month_start = next_month_start.replace(month=next_month_start.month + 1, day=1)
    
    next_month_end = next_next_month_start - timedelta(days=1)
    
    start_date = current_month_start.strftime('%Y-%m-%d')
    end_date = next_month_end.strftime('%Y-%m-%d')
    current_month_name = today.strftime('%Y年%m月')
    next_month_name = next_month_start.strftime('%Y年%m月')
    
    prompt = f"""你是專業的台股分析師。請生成 {current_month_name} 和 {next_month_name} 的重要財經事件（{start_date} 到 {end_date}）。

**重要要求**：
1. 必須生成 25-30 個事件
2. 台灣事件至少 15 個（法說會、政府政策、經濟數據）
3. 美國事件 8-10 個（科技財報、經濟數據、FOMC）
4. 對於 FOMC 會議和主要法說會，請搜尋確認正確日期
5. 其他事件可根據慣例估計（如 PMI 月初、CPI 月中）

JSON 格式（必須包含所有欄位）：
[
  {{
    "id": "MMDD-關鍵字",
    "date": "YYYY-MM-DD",
    "title": "事件標題（15字內）",
    "market": "TW/US/CN/Global",
    "type": "corporate/critical/hot",
    "trend": "bull/bear/neutral",
    "relatedStocks": ["股票名稱 (代碼)", ...],
    "description": "事件描述（80字內）",
    "strategy": "操作策略（80字內）"
  }}
]

**必須包含的事件類型**：
- 台灣：台積電、聯發科、鴻海、台達電、日月光等法說會，央行會議，GDP/PMI/CPI/外銷訂單，政府政策
- 美國：NVIDIA、Apple、AMD 等財報，FOMC 會議，CPI/PPI/非農就業

只輸出 JSON 陣列，確保 25-30 個事件。"""

    # 使用 Google Search Grounding
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            tools=[types.Tool(google_search=types.GoogleSearch())],
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
        print("正在生成當月和下個月的重要事件...")
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
