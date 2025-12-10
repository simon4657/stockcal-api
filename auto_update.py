#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本
每日自動生成熱點、策略和事件資料
方案 B：完全動態生成當月（N）和下個月（N+1）的重要事件（加強台灣事件）
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
    """使用 Gemini 生成當月（N）和下個月（N+1）的重要事件（加強台灣事件）"""
    
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
    
    prompt = f"""你是一位專業的台股分析師。請根據今天 ({TODAY}) 的市場狀況，預測 {current_month_name} 和 {next_month_name} 兩個月（{start_date} 到 {end_date}）可能發生的重要事件。

**重要提醒**：請特別關注台灣本土事件，至少包含 50% 以上的台灣相關事件。

請以 JSON 格式輸出 10-15 個事件，包含以下欄位：
- id: 唯一識別碼 (格式: MM-DD-關鍵字，例如: 11-25-tsmc)
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
    "id": "11-28-tsmc",
    "date": "2025-11-28",
    "title": "台積電法說會",
    "market": "TW",
    "type": "corporate",
    "trend": "bull",
    "relatedStocks": ["台積電 (2330)", "聯發科 (2454)", "弘塑 (3131)", "家登 (3680)"],
    "description": "台積電召開法人說明會，公布 Q4 財報與 2026 年展望。市場關注先進製程進度、資本支出與 AI 晶片需求。",
    "strategy": "法說前可提前布局，若展望優於預期，設備供應鏈將受惠。注意法說後外資動向。"
  }},
  {{
    "id": "12-05-policy",
    "date": "2025-12-05",
    "title": "行政院產業政策說明",
    "market": "TW",
    "type": "critical",
    "trend": "neutral",
    "relatedStocks": ["台積電 (2330)", "聯發科 (2454)", "鴻海 (2317)", "長榮 (2603)"],
    "description": "行政院將說明 2026 年產業發展政策，可能涉及半導體、綠能、國防等重點產業補助與稅務優惠。",
    "strategy": "關注政策受惠產業，若有明確補助方案，相關個股可逢低布局。"
  }}
]

請根據以下資訊生成事件，**務必包含大量台灣事件**：

### 台灣重要事件（必須包含）：
1. **權值股法說會**：
   - 台積電 (2330) 法說會
   - 聯發科 (2454) 法說會
   - 鴻海 (2317) 法說會
   - 台達電 (2308) 法說會
   - 日月光投控 (3711) 法說會
   - 大立光 (3008) 法說會

2. **政府政策與會議**：
   - 行政院產業政策說明
   - 立法院重要法案審查（如產創條例、電業法等）
   - 經濟部產業補助公告
   - 國發會經濟展望報告
   - 金管會金融政策說明

3. **央行與金融**：
   - 台灣央行理監事會議（利率決策）
   - 金管會保險業監理會議
   - 證交所重大宣布

4. **經濟數據**：
   - 台灣 GDP 成長率公布
   - 外銷訂單統計
   - PMI 指數公布
   - 消費者物價指數 (CPI)
   - 失業率統計

5. **產業重要事件**：
   - COMPUTEX 台北國際電腦展
   - 半導體展覽
   - 電動車產業論壇
   - 綠能產業展覽

6. **除權息旺季**：
   - 重要個股除權息日（台積電、鴻海等）

### 美國重要事件（也要包含）：
1. **科技巨頭財報**：NVIDIA、AMD、Dell、HP、Broadcom、Apple
2. **經濟數據**：CPI、PPI、非農就業、消費者信心指數、PMI
3. **央行會議**：Fed FOMC 會議
4. **產業事件**：AI 新品發表、半導體展會

### 其他國際事件：
1. 中國經濟數據
2. 日本央行會議
3. 歐洲經濟數據

**注意事項**：
- 日期必須真實合理
- 台灣事件必須佔 50% 以上
- 事件必須具體且可能發生
- 相關個股必須真實存在
- 涵蓋不同類型的事件
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
        print("正在生成當月和下個月的重要事件（加強台灣事件）...")
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
