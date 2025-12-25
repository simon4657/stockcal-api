from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
import json
import os
from google import genai
from google.genai import types

app = FastAPI(title="StockCal API", version="1.0.0")

# CORS 設定 - 允許前端跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制為特定網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料模型
class StockEvent(BaseModel):
    id: str
    date: str
    title: str
    market: Literal['US', 'TW', 'Global']
    type: Literal['critical', 'hot', 'corporate', 'macro', 'holiday']
    trend: Literal['bull', 'bear', 'neutral', 'volatile']
    relatedStocks: Optional[List[str]] = None
    description: str
    strategy: str

class HotTrend(BaseModel):
    id: str
    name: str
    strength: int
    trend: Literal['up', 'down', 'neutral', 'volatile']
    stocks: List[str]
    reason: str
    updatedAt: str

class Strategy(BaseModel):
    id: str
    title: str
    type: Literal['bull', 'bear', 'neutral', 'volatile']
    desc: str
    risk: Literal['低', '中', '高']
    target: str
    updatedAt: str

# Gemini API 設定
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# 資料檔案路徑
DATA_DIR = os.path.dirname(__file__)
EVENTS_FILE = os.path.join(DATA_DIR, "data_events.json")
HOT_TRENDS_FILE = os.path.join(DATA_DIR, "data_hot_trends.json")
STRATEGIES_FILE = os.path.join(DATA_DIR, "data_strategies.json")

# 初始化 Gemini 客戶端
def init_gemini():
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

# 載入資料的輔助函數
def load_json_data(filepath: str, default_data: list):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_data

def save_json_data(filepath: str, data: list):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# API 端點
@app.get("/")
def read_root():
    return {
        "message": "StockCal API",
        "version": "1.0.0",
        "endpoints": {
            "events": "/api/events",
            "hot_trends": "/api/hot-trends",
            "strategies": "/api/strategies",
            "analyze_hot_trend": "/api/analyze/hot-trend/{trend_id}",
            "analyze_strategy": "/api/analyze/strategy/{strategy_id}"
        }
    }

@app.get("/api/events", response_model=List[StockEvent])
def get_events():
    """獲取月度事件（每月更新）"""
    default_events = []
    events = load_json_data(EVENTS_FILE, default_events)
    return events

@app.get("/api/hot-trends", response_model=List[HotTrend])
def get_hot_trends():
    """獲取每日熱點（每日更新）"""
    default_trends = []
    trends = load_json_data(HOT_TRENDS_FILE, default_trends)
    return trends

@app.get("/api/strategies", response_model=List[Strategy])
def get_strategies():
    """獲取每日策略（每日更新）"""
    default_strategies = []
    strategies = load_json_data(STRATEGIES_FILE, default_strategies)
    return strategies

@app.get("/api/analyze/hot-trend/{trend_id}")
def analyze_hot_trend(trend_id: str):
    """使用 Gemini AI 深度分析熱點"""
    # 載入熱點資料
    trends = load_json_data(HOT_TRENDS_FILE, [])
    trend = next((t for t in trends if t['id'] == trend_id), None)
    
    if not trend:
        raise HTTPException(status_code=404, detail="熱點不存在")
    
    # 初始化 Gemini
    client = init_gemini()
    if not client:
        raise HTTPException(status_code=500, detail="AI 分析服務暫時無法使用")
    
    # 生成分析
    prompt = f"""你是專業的台股分析師。請針對以下熱點族群進行深度分析：

族群名稱：{trend['name']}
資金強度：{trend['strength']}/100
趨勢：{trend['trend']}
相關個股：{', '.join(trend['stocks'])}
熱點原因：{trend['reason']}

請提供以下分析（以 JSON 格式輸出）：

{{
  "technical_analysis": "技術面分析（支撐壓力、趨勢判斷、量價關係，150字內）",
  "fundamental_analysis": "基本面分析（產業前景、競爭優勢、成長動能，150字內）",
  "risk_assessment": "風險評估（潛在風險、注意事項，100字內）",
  "trading_suggestion": {{
    "entry_point": "建議進場點位或時機",
    "stop_loss": "停損建議",
    "take_profit": "停利建議",
    "holding_period": "建議持有期間"
  }},
  "key_stocks": [
    {{
      "name": "個股名稱 (代碼)",
      "reason": "推薦原因（50字內）",
      "rating": "評級（強力推薦/推薦/中性）"
    }}
  ]
}}

只輸出 JSON，不要其他說明文字。"""
    
    try:
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
        
        # 移除 markdown 標記
        if '```json' in text:
            text = text[text.find('```json') + 7:]
        elif '```' in text:
            text = text[text.find('```') + 3:]
        
        if '```' in text:
            text = text[:text.rfind('```')]
        
        # 尋找 JSON 開始位置
        if not text.strip().startswith('{'):
            start = text.find('{')
            if start != -1:
                text = text[start:]
        
        analysis = json.loads(text.strip())
        
        return {
            "trend": trend,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失敗: {str(e)}")

@app.get("/api/analyze/strategy/{strategy_id}")
def analyze_strategy(strategy_id: str):
    """使用 Gemini AI 深度分析策略"""
    # 載入策略資料
    strategies = load_json_data(STRATEGIES_FILE, [])
    strategy = next((s for s in strategies if s['id'] == strategy_id), None)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 初始化 Gemini
    client = init_gemini()
    if not client:
        raise HTTPException(status_code=500, detail="AI 分析服務暫時無法使用")
    
    # 生成分析
    prompt = f"""你是專業的台股操盤手。請針對以下操作策略進行深度分析：

策略標題：{strategy['title']}
策略類型：{strategy['type']}
策略描述：{strategy['desc']}
風險等級：{strategy['risk']}
關注目標：{strategy['target']}

請提供以下分析（以 JSON 格式輸出）：

{{
  "strategy_rationale": "策略原理（為什麼這個策略適合當前市場，150字內）",
  "execution_details": {{
    "entry_timing": "具體進場時機（何時進場最佳）",
    "position_sizing": "倉位配置建議（如何分配資金）",
    "exit_strategy": "出場策略（何時獲利了結或停損）"
  }},
  "risk_management": {{
    "max_loss": "最大可能虧損",
    "hedge_method": "風險對沖方法",
    "warning_signs": "需要警惕的訊號"
  }},
  "historical_performance": "歷史表現（類似情況下的成功案例，100字內）",
  "success_probability": "成功機率評估（高/中/低）",
  "alternative_strategies": [
    {{
      "name": "替代策略名稱",
      "description": "簡短描述（50字內）"
    }}
  ]
}}

只輸出 JSON，不要其他說明文字。"""
    
    try:
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
        
        # 移除 markdown 標記
        if '```json' in text:
            text = text[text.find('```json') + 7:]
        elif '```' in text:
            text = text[text.find('```') + 3:]
        
        if '```' in text:
            text = text[:text.rfind('```')]
        
        # 尋找 JSON 開始位置
        if not text.strip().startswith('{'):
            start = text.find('{')
            if start != -1:
                text = text[start:]
        
        analysis = json.loads(text.strip())
        
        return {
            "strategy": strategy,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失敗: {str(e)}")

@app.get("/health")
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
