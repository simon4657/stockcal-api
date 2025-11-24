#!/usr/bin/env python3
"""
StockCal 自動資料更新腳本
每日自動生成熱點和策略資料
"""

import json
import os
from datetime import datetime
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
        
        print(f"[{datetime.now()}] 資料更新完成！")
        return True
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        return False

if __name__ == '__main__':
    success = update_data_files()
    exit(0 if success else 1)
