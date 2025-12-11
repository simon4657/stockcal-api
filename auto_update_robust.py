#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本 - 穩健版
加強錯誤處理和日誌輸出
"""
import json
import os
import sys
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 配置
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TODAY = datetime.now().strftime('%Y-%m-%d')

def log(message, level="INFO"):
    """輸出日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}", flush=True)

def extract_json(text):
    """從文本中提取 JSON"""
    log(f"原始回應長度: {len(text)} 字元")
    log(f"前 200 字元: {text[:200]}...")
    
    # 移除 markdown 標記
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    
    if text.endswith('```'):
        text = text[:-3]
    
    text = text.strip()
    log(f"處理後長度: {len(text)} 字元")
    
    try:
        data = json.loads(text)
        log(f"✓ JSON 解析成功", "SUCCESS")
        return data
    except json.JSONDecodeError as e:
        log(f"JSON 解析錯誤: {e}", "ERROR")
        log(f"錯誤位置附近: {text[max(0, e.pos-50):e.pos+50]}", "ERROR")
        raise

def init_gemini():
    """初始化 Gemini 客戶端"""
    if not GEMINI_API_KEY:
        log("GEMINI_API_KEY 環境變數未設定", "ERROR")
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    log("✓ Gemini 客戶端初始化成功", "SUCCESS")
    return client

def generate_hot_trends(client):
    """使用 Gemini 生成每日熱點"""
    log("開始生成每日熱點...")
    
    prompt = f"""你是一位專業的台股分析師。請根據今天 ({TODAY}) 的市場狀況，生成 4 個最熱門的族群或主題。

請以 JSON 格式輸出，包含以下欄位：
- id: 唯一識別碼 (格式: hot-1, hot-2...)
- name: 族群名稱
- strength: 資金強度 (0-100)
- trend: 趨勢 (up/down/neutral/volatile)
- stocks: 相關個股列表 (3-5 檔，格式: "股票名稱 (代碼)")
- reason: 熱點原因說明 (50字內)
- updatedAt: 更新日期 ({TODAY})

只輸出 JSON 陣列，不要其他說明文字。"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        log("✓ API 呼叫成功", "SUCCESS")
        return extract_json(response.text)
    except Exception as e:
        log(f"生成熱點失敗: {e}", "ERROR")
        raise

def generate_strategies(client):
    """使用 Gemini 生成每日策略"""
    log("開始生成每日策略...")
    
    prompt = f"""你是一位專業的台股操盤手。請根據今天 ({TODAY}) 的市場狀況，生成 3 個操作策略建議。

請以 JSON 格式輸出，包含以下欄位：
- id: 唯一識別碼 (格式: st-1, st-2...)
- title: 策略標題
- type: 策略類型 (bull/bear/neutral/volatile)
- desc: 策略描述 (80字內)
- risk: 風險等級 (低/中/高)
- target: 關注目標
- updatedAt: 更新日期 ({TODAY})

只輸出 JSON 陣列，不要其他說明文字。"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        log("✓ API 呼叫成功", "SUCCESS")
        return extract_json(response.text)
    except Exception as e:
        log(f"生成策略失敗: {e}", "ERROR")
        raise

def generate_future_events(client):
    """使用 Gemini 生成當月和下個月的重要事件"""
    log("開始生成未來事件...")
    
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
    
    log(f"日期範圍: {start_date} 到 {end_date}")
    
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

    try:
        log("正在呼叫 Gemini API（使用 Google Search）...")
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        log("✓ API 呼叫成功", "SUCCESS")
        
        events = extract_json(response.text)
        
        # 過濾並排序事件
        today_dt = datetime.now()
        valid_events = []
        
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                if event_date > today_dt:
                    valid_events.append(event)
                else:
                    log(f"跳過過去的事件: {event['date']} {event['title']}", "WARN")
            except Exception as e:
                log(f"事件日期解析錯誤: {event.get('date', 'N/A')} - {e}", "WARN")
                continue
        
        # 按日期排序
        valid_events.sort(key=lambda x: x['date'])
        
        log(f"✓ 生成 {len(valid_events)} 個有效事件", "SUCCESS")
        return valid_events
        
    except Exception as e:
        log(f"生成事件失敗: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        raise

def update_data_files():
    """更新資料檔案"""
    try:
        log("=" * 60)
        log("開始自動更新資料")
        log("=" * 60)
        
        # 初始化 Gemini
        client = init_gemini()
        
        # 生成熱點資料
        log("\n--- 步驟 1/3: 生成每日熱點 ---")
        hot_trends = generate_hot_trends(client)
        with open('data_hot_trends.json', 'w', encoding='utf-8') as f:
            json.dump(hot_trends, f, ensure_ascii=False, indent=2)
        log(f"✓ 熱點資料已更新 ({len(hot_trends)} 項)", "SUCCESS")
        
        # 生成策略資料
        log("\n--- 步驟 2/3: 生成每日策略 ---")
        strategies = generate_strategies(client)
        with open('data_strategies.json', 'w', encoding='utf-8') as f:
            json.dump(strategies, f, ensure_ascii=False, indent=2)
        log(f"✓ 策略資料已更新 ({len(strategies)} 項)", "SUCCESS")
        
        # 生成未來事件
        log("\n--- 步驟 3/3: 生成未來事件 ---")
        events = generate_future_events(client)
        with open('data_events.json', 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        log(f"✓ 事件資料已更新 ({len(events)} 項)", "SUCCESS")
        
        # 顯示事件摘要
        log("\n" + "=" * 60)
        log("事件摘要")
        log("=" * 60)
        tw_count = sum(1 for e in events if e['market'] == 'TW')
        us_count = sum(1 for e in events if e['market'] == 'US')
        other_count = len(events) - tw_count - us_count
        
        log(f"總事件數: {len(events)}")
        log(f"  - 台灣事件: {tw_count} 個 ({tw_count/len(events)*100:.1f}%)")
        log(f"  - 美國事件: {us_count} 個 ({us_count/len(events)*100:.1f}%)")
        log(f"  - 其他事件: {other_count} 個")
        
        log("\n前 5 個事件：")
        for i, event in enumerate(events[:5], 1):
            log(f"  {i}. {event['date']}: {event['title']} ({event['market']})")
        
        if len(events) > 5:
            log(f"  ... 還有 {len(events) - 5} 個事件")
        
        log("\n" + "=" * 60)
        log("資料更新完成！", "SUCCESS")
        log("=" * 60)
        return True
        
    except Exception as e:
        log(f"更新失敗: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_data_files()
    sys.exit(0 if success else 1)
