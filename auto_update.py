#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本
每日自動生成熱點、策略和事件資料
"""
import json
import os
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 配置
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TODAY = datetime.now().strftime('%Y-%m-%d')

# 固定的重要事件（不會被刪除）
FIXED_EVENTS = [
    {
        "id": "12-10-fomc",
        "date": "2025-12-10",
        "title": "CPI 公布 & FOMC",
        "market": "US",
        "type": "critical",
        "trend": "neutral"
    },
    {
        "id": "01-15-tsmc",
        "date": "2026-01-15",
        "title": "台積電 Q4 法說會",
        "market": "TW",
        "type": "critical",
        "trend": "bull"
    }
]

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

def generate_event_details(client, event):
    """使用 Gemini 為特定事件生成詳細內容"""
    
    prompt = f"""你是一位專業的台股分析師。請針對以下事件生成詳細的分析內容：

事件標題：{event['title']}
事件日期：{event['date']}
市場：{event['market']}
今天日期：{TODAY}

請以 JSON 格式輸出，包含以下欄位：
- relatedStocks: 相關個股列表 (3-5 檔，格式: "股票名稱 (代碼)")
- description: 事件描述與重點 (80字內)
- strategy: 操作策略建議 (80字內)

範例格式：
{{
  "relatedStocks": ["台積電 (2330)", "聯發科 (2454)", "日月光 (2311)"],
  "description": "台積電法說會將公布 2026 年資本支出與先進製程進度，影響全球半導體供應鏈。",
  "strategy": "若資本支出超過預期，設備股將受惠。建議法說前布局，法說後視指引調整。"
}}

請根據當前市場狀況和該事件的重要性生成內容。
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

def generate_dynamic_events(client):
    """使用 Gemini 生成未來 7 天的動態事件"""
    
    # 計算未來 7 天的日期範圍
    today = datetime.now()
    future_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
    
    prompt = f"""你是一位專業的台股分析師。請根據今天 ({TODAY}) 的市場狀況，預測未來 7 天內可能發生的重要事件。

請以 JSON 格式輸出 2-3 個事件，包含以下欄位：
- id: 唯一識別碼 (格式: MM-DD-關鍵字)
- date: 事件日期 (YYYY-MM-DD，必須在 {future_dates[0]} 到 {future_dates[-1]} 之間)
- title: 事件標題 (簡短有力)
- market: 市場 (TW/US/CN)
- type: 事件類型 (hot/corporate/critical)
- trend: 預期趨勢 (bull/bear/neutral)
- relatedStocks: 相關個股列表 (3-5 檔)
- description: 事件描述 (80字內)
- strategy: 操作策略 (80字內)

範例格式：
[
  {{
    "id": "11-25-nvidia",
    "date": "2025-11-25",
    "title": "輝達財報公布",
    "market": "US",
    "type": "corporate",
    "trend": "bull",
    "relatedStocks": ["廣達 (2382)", "緯創 (3231)", "技嘉 (2376)"],
    "description": "輝達 Q3 財報將公布，市場關注 AI 晶片需求與未來展望。",
    "strategy": "若財報優於預期，台系供應鏈將受惠，可提前布局。"
  }}
]

請根據以下資訊生成：
1. 近期重要財報發布
2. 重大經濟數據公布
3. 產業重要事件
4. 政策或法規變動

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

def update_events(client):
    """更新事件資料（混合模式）"""
    
    print("正在更新事件資料...")
    
    # 1. 讀取現有事件
    try:
        with open('data_events.json', 'r', encoding='utf-8') as f:
            existing_events = json.load(f)
    except:
        existing_events = []
    
    # 2. 過濾掉過期的動態事件（保留固定事件）
    today = datetime.now()
    fixed_event_ids = [e['id'] for e in FIXED_EVENTS]
    
    valid_events = []
    for event in existing_events:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        # 保留未來的事件，或者是固定事件
        if event_date >= today or event['id'] in fixed_event_ids:
            valid_events.append(event)
    
    # 3. 更新固定事件的詳細內容
    updated_events = []
    for event in valid_events:
        if event['id'] in fixed_event_ids:
            print(f"  更新固定事件: {event['title']}")
            details = generate_event_details(client, event)
            event.update(details)
        updated_events.append(event)
    
    # 4. 生成新的動態事件
    print("  生成新的動態事件...")
    new_events = generate_dynamic_events(client)
    
    # 5. 合併事件（避免重複）
    existing_ids = {e['id'] for e in updated_events}
    for new_event in new_events:
        if new_event['id'] not in existing_ids:
            updated_events.append(new_event)
    
    # 6. 按日期排序
    updated_events.sort(key=lambda x: x['date'])
    
    # 7. 保存
    with open('data_events.json', 'w', encoding='utf-8') as f:
        json.dump(updated_events, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 事件資料已更新 ({len(updated_events)} 項)")
    return updated_events

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
        
        # 更新事件資料
        events = update_events(client)
        
        print(f"[{datetime.now()}] 資料更新完成！")
        return True
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_data_files()
    exit(0 if success else 1)
