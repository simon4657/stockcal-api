from fastapi import FastAPI, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
import json
import os
from google import genai
from google.genai import types

app = FastAPI(title="StockCal API", version="2.0.0")

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
    market: Literal['US', 'TW', 'CN', 'Global']
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

class FeedbackRequest(BaseModel):
    feedback: str

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

# JSON 提取輔助函數
def extract_json_from_response(text: str) -> dict:
    """從 Gemini 回應中提取 JSON"""
    # 移除 markdown 標記
    if '```json' in text:
        text = text[text.find('```json') + 7:]
    elif '```' in text:
        text = text[text.find('```') + 3:]
    
    if '```' in text:
        text = text[:text.rfind('```')]
    
    # 尋找 JSON 開始位置
    text = text.strip()
    if not text.startswith('{') and not text.startswith('['):
        start = text.find('{')
        if start == -1:
            start = text.find('[')
        if start != -1:
            text = text[start:]
    
    return json.loads(text.strip())

# AI 分析核心函數
def generate_ai_analysis(prompt: str, api_key: Optional[str] = None, feedback: Optional[str] = None):
    """使用 Gemini 2.0 Flash Thinking 生成分析"""
    # 優先使用傳入的 API key，否則使用環境變數
    key_to_use = api_key or GEMINI_API_KEY
    if not key_to_use:
        raise HTTPException(status_code=500, detail="請先在設定頁面輸入 Gemini API Key")
    
    client = genai.Client(api_key=key_to_use)
    if not client:
        raise HTTPException(status_code=500, detail="AI 分析服務暫時無法使用")
    
    # 如果有回饋，加入到 prompt 中
    if feedback:
        prompt += f"\n\n**使用者回饋**：{feedback}\n請根據使用者的回饋重新生成分析，修正錯誤之處。"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',  # 使用思考型模型
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # 降低溫度以提高準確性
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        
        return extract_json_from_response(response.text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失敗: {str(e)}")

# API 端點
@app.get("/")
def read_root():
    return {
        "message": "StockCal API v2.0",
        "version": "2.0.0",
        "ai_model": "Gemini 2.5 Pro",
        "endpoints": {
            "events": "/api/events",
            "hot_trends": "/api/hot-trends",
            "strategies": "/api/strategies",
            "analyze_event": "/api/analyze/event/{event_id}",
            "analyze_hot_trend": "/api/analyze/hot-trend/{trend_id}",
            "analyze_strategy": "/api/analyze/strategy/{strategy_id}",
            "regenerate_event": "/api/analyze/event/{event_id}/regenerate",
            "regenerate_hot_trend": "/api/analyze/hot-trend/{trend_id}/regenerate",
            "regenerate_strategy": "/api/analyze/strategy/{strategy_id}/regenerate"
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

# ============ 事件分析 ============

@app.get("/api/analyze/event/{event_id}")
def analyze_event(event_id: str, x_api_key: Optional[str] = Header(None)):
    """使用 Gemini 2.0 Flash Thinking 深度分析事件"""
    events = load_json_data(EVENTS_FILE, [])
    event = next((e for e in events if e['id'] == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    prompt = f"""你是專業的財經分析師。請針對以下重要事件進行深度分析：

事件日期：{event['date']}
事件標題：{event['title']}
市場：{event['market']}
事件類型：{event['type']}
市場趨勢：{event['trend']}
相關個股：{', '.join(event.get('relatedStocks', []))}
事件描述：{event['description']}
操作策略：{event['strategy']}

請提供以下分析（以 JSON 格式輸出）：

{{
  "event_impact": {{
    "short_term": "短期影響（1-2週）分析，150字內",
    "medium_term": "中期影響（1-3個月）分析，150字內",
    "long_term": "長期影響（3個月以上）分析，100字內"
  }},
  "market_reaction": {{
    "expected_volatility": "預期波動程度（高/中/低）",
    "key_indicators": ["關鍵指標1", "關鍵指標2", "關鍵指標3"],
    "sentiment": "市場情緒預測（樂觀/謹慎/悲觀）"
  }},
  "trading_strategy": {{
    "before_event": "事件前操作建議（100字內）",
    "during_event": "事件當天操作建議（100字內）",
    "after_event": "事件後操作建議（100字內）",
    "risk_control": "風險控制要點（80字內）"
  }},
  "affected_sectors": [
    {{
      "sector": "受影響產業",
      "impact": "影響程度（正面/負面/中性）",
      "reason": "影響原因（50字內）"
    }}
  ],
  "key_stocks_to_watch": [
    {{
      "name": "個股名稱 (代碼)",
      "action": "操作建議（買入/持有/觀望/賣出）",
      "reason": "推薦原因（50字內）",
      "target_price": "目標價位或漲跌幅預估"
    }}
  ],
  "historical_reference": "歷史類似事件參考（100字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "event": event,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro"
    }

@app.post("/api/analyze/event/{event_id}/regenerate")
def regenerate_event_analysis(event_id: str, feedback: FeedbackRequest = Body(...), x_api_key: Optional[str] = Header(None)):
    """根據使用者回饋重新生成事件分析"""
    events = load_json_data(EVENTS_FILE, [])
    event = next((e for e in events if e['id'] == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    prompt = f"""你是專業的財經分析師。請針對以下重要事件進行深度分析：

事件日期：{event['date']}
事件標題：{event['title']}
市場：{event['market']}
事件類型：{event['type']}
市場趨勢：{event['trend']}
相關個股：{', '.join(event.get('relatedStocks', []))}
事件描述：{event['description']}
操作策略：{event['strategy']}

請提供以下分析（以 JSON 格式輸出）：

{{
  "event_impact": {{
    "short_term": "短期影響（1-2週）分析，150字內",
    "medium_term": "中期影響（1-3個月）分析，150字內",
    "long_term": "長期影響（3個月以上）分析，100字內"
  }},
  "market_reaction": {{
    "expected_volatility": "預期波動程度（高/中/低）",
    "key_indicators": ["關鍵指標1", "關鍵指標2", "關鍵指標3"],
    "sentiment": "市場情緒預測（樂觀/謹慎/悲觀）"
  }},
  "trading_strategy": {{
    "before_event": "事件前操作建議（100字內）",
    "during_event": "事件當天操作建議（100字內）",
    "after_event": "事件後操作建議（100字內）",
    "risk_control": "風險控制要點（80字內）"
  }},
  "affected_sectors": [
    {{
      "sector": "受影響產業",
      "impact": "影響程度（正面/負面/中性）",
      "reason": "影響原因（50字內）"
    }}
  ],
  "key_stocks_to_watch": [
    {{
      "name": "個股名稱 (代碼)",
      "action": "操作建議（買入/持有/觀望/賣出）",
      "reason": "推薦原因（50字內）",
      "target_price": "目標價位或漲跌幅預估"
    }}
  ],
  "historical_reference": "歷史類似事件參考（100字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key, feedback=feedback.feedback)
    
    return {
        "event": event,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro",
        "regenerated": True,
        "feedback_applied": feedback.feedback
    }

# ============ 熱點分析 ============

@app.get("/api/analyze/hot-trend/{trend_id}")
def analyze_hot_trend(trend_id: str, x_api_key: Optional[str] = Header(None)):
    """使用 Gemini 2.0 Flash Thinking 深度分析熱點"""
    trends = load_json_data(HOT_TRENDS_FILE, [])
    trend = next((t for t in trends if t['id'] == trend_id), None)
    
    if not trend:
        raise HTTPException(status_code=404, detail="熱點不存在")
    
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
      "rating": "評級（強力推薦/推薦/中性）",
      "entry_price": "建議進場價位"
    }}
  ],
  "market_outlook": "市場展望（100字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "trend": trend,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro"
    }

@app.post("/api/analyze/hot-trend/{trend_id}/regenerate")
def regenerate_hot_trend_analysis(trend_id: str, feedback: FeedbackRequest = Body(...), x_api_key: Optional[str] = Header(None)):
    """根據使用者回饋重新生成熱點分析"""
    trends = load_json_data(HOT_TRENDS_FILE, [])
    trend = next((t for t in trends if t['id'] == trend_id), None)
    
    if not trend:
        raise HTTPException(status_code=404, detail="熱點不存在")
    
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
      "rating": "評級（強力推薦/推薦/中性）",
      "entry_price": "建議進場價位"
    }}
  ],
  "market_outlook": "市場展望（100字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key, feedback=feedback.feedback)
    
    return {
        "trend": trend,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro",
        "regenerated": True,
        "feedback_applied": feedback.feedback
    }

# ============ 策略分析 ============

@app.get("/api/analyze/strategy/{strategy_id}")
def analyze_strategy(strategy_id: str, x_api_key: Optional[str] = Header(None)):
    """使用 Gemini 2.0 Flash Thinking 深度分析策略"""
    strategies = load_json_data(STRATEGIES_FILE, [])
    strategy = next((s for s in strategies if s['id'] == strategy_id), None)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
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
  ],
  "market_conditions": "適用的市場條件（80字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "strategy": strategy,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro"
    }

@app.post("/api/analyze/strategy/{strategy_id}/regenerate")
def regenerate_strategy_analysis(strategy_id: str, feedback: FeedbackRequest = Body(...), x_api_key: Optional[str] = Header(None)):
    """根據使用者回饋重新生成策略分析"""
    strategies = load_json_data(STRATEGIES_FILE, [])
    strategy = next((s for s in strategies if s['id'] == strategy_id), None)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
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
  ],
  "market_conditions": "適用的市場條件（80字內）",
  "confidence_level": "分析信心度（高/中/低）"
}}

只輸出 JSON，不要其他說明文字。"""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key, feedback=feedback.feedback)
    
    return {
        "strategy": strategy,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro",
        "regenerated": True,
        "feedback_applied": feedback.feedback
    }

@app.get("/health")
def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "ai_model": "gemini-2.5-pro"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
