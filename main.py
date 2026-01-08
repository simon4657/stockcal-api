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
# 開放式格式，輸出 Markdown 文本
def generate_ai_analysis(prompt: str, api_key: Optional[str] = None, feedback: Optional[str] = None):
    """使用 Gemini 2.5 Pro 生成開放式分析"""
    # 優先使用傳入的 API key，否則使用環境變數
    key_to_use = api_key or GEMINI_API_KEY
    if not key_to_use:
        raise HTTPException(status_code=500, detail="請先在設定頁面輸入 Gemini API Key")
    
    client = genai.Client(api_key=key_to_use)
    if not client:
        raise HTTPException(status_code=500, detail="AI 分析服務暫時無法使用")
    
    # 如果有回饋，加入到 prompt 中
    if feedback:
        prompt += f"\n\n---\n\n**使用者回饋**：{feedback}\n\n請根據上述回饋重新生成分析，修正錯誤之處，並提供更深入的見解。"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,  # 提高溫度以增加創意和深度
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        
        # 直接返回 Markdown 文本，不需要 JSON 解析
        return response.text.strip()
        
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
    
    prompt = f"""你是一位資深的財經分析師，擁有豐富的市場經驗和深厚的產業知識。

請針對以下重要事件進行深入、全面的分析：

## 事件資訊
- **日期**：{event['date']}
- **標題**：{event['title']}
- **市場**：{event['market']}
- **類型**：{event['type']}
- **市場趨勢**：{event['trend']}
- **相關個股**：{', '.join(event.get('relatedStocks', []))}
- **描述**：{event['description']}
- **建議策略**：{event['strategy']}

## 分析要求

請以專業分析師的角度，自由發揮地提供深入分析。不需要拘泥於固定格式，請根據事件特性選擇最適合的分析角度和內容。

建議可以涵蓋（但不限於）以下面向：

1. **事件解讀與背景** - 這個事件的核心意義、經濟邏輯、與總體經濟環境的關聯
2. **市場影響分析** - 對股市、匯市、債市的影響，短中長期影響路徑，產業鏈波及效應
3. **投資機會與風險** - 具體投資機會、風險點、進場時機、倉位配置、停損停利建議
4. **個股深度分析** - 重點個股的基本面變化、技術面支撐壓力、估值分析、目標價位
5. **歷史經驗與前瞻** - 過去類似事件的市場反應、這次的不同之處、未來發展情境

## 寫作要求
- 使用 Markdown 格式，包含清晰的標題和段落
- 提供具體的數據、價位、時間點
- 避免過於籠統的描述
- 可以大膽提出觀點，但要說明理由
- 篇幅不限，請充分展開分析

請開始你的深度分析："""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "event": event,
        "analysis": analysis,
        "format": "markdown",
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
    
    prompt = f"""你是一位資深的財經分析師，擁有豐富的市場經驗和深厚的產業知識。

請針對以下重要事件進行深入、全面的分析：

## 事件資訊
- **日期**：{event['date']}
- **標題**：{event['title']}
- **市場**：{event['market']}
- **類型**：{event['type']}
- **市場趨勢**：{event['trend']}
- **相關個股**：{', '.join(event.get('relatedStocks', []))}
- **描述**：{event['description']}
- **建議策略**：{event['strategy']}

## 分析要求

請以專業分析師的角度，自由發揮地提供深入分析。不需要拘泥於固定格式，請根據事件特性選擇最適合的分析角度和內容。

建議可以涵蓋（但不限於）以下面向：

1. **事件解讀與背景** - 這個事件的核心意義、經濟邏輯、與總體經濟環境的關聯
2. **市場影響分析** - 對股市、匯市、債市的影響，短中長期影響路徑，產業鏈波及效應
3. **投資機會與風險** - 具體投資機會、風險點、進場時機、倉位配置、停損停利建議
4. **個股深度分析** - 重點個股的基本面變化、技術面支撐壓力、估值分析、目標價位
5. **歷史經驗與前瞻** - 過去類似事件的市場反應、這次的不同之處、未來發展情境

## 寫作要求
- 使用 Markdown 格式，包含清晰的標題和段落
- 提供具體的數據、價位、時間點
- 避免過於籠統的描述
- 可以大膽提出觀點，但要說明理由
- 篇幅不限，請充分展開分析

請開始你的深度分析："""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key, feedback=feedback.feedback)
    
    return {
        "event": event,
        "analysis": analysis,
        "format": "markdown",
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
    
    prompt = f"""你是一位資深的台股分析師，擁有豐富的市場經驗和深厚的產業知識。

請針對以下熱點族群進行深入、全面的分析：

## 熱點資訊
- **族群名稱**：{trend['name']}
- **資金強度**：{trend['strength']}/100
- **趋勢**：{trend['trend']}
- **相關個股**：{', '.join(trend['stocks'])}
- **熱點原因**：{trend['reason']}

## 分析要求

請以專業分析師的角度，自由發揮地提供深入分析。不需要拘泥於固定格式，請根據熱點特性選擇最適合的分析角度和內容。

建議可以涵蓋（但不限於）以下面向：

1. **產業趨勢與背景** - 這個熱點的形成原因、產業連結、與總體經濟的關聯
2. **技術面與資金面** - 資金流向、量價關係、支撐壓力、技術型態
3. **基本面分析** - 產業前景、競爭格局、成長動能、獲利能力
4. **重點個股深度剖析** - 選股邏輯、基本面變化、技術面位置、估值分析、目標價
5. **風險與機會** - 潛在風險、注意事項、投資機會、進場時機
6. **操作策略** - 進出場時機、個位配置、停損停利、持有期間

## 寫作要求
- 使用 Markdown 格式，包含清晰的標題和段落
- 提供具體的數據、價位、時間點
- 避免過於籠統的描述
- 可以大膽提出觀點，但要說明理由
- 篇幅不限，請充分展開分析

請開始你的深度分析："""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "trend": trend,
        "analysis": analysis,
        "format": "markdown",
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
        "format": "markdown",
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
    
    prompt = f"""你是一位資深的台股操盤手，擁有多年的實戰經驗和穩健的獲利紀錄。

請針對以下操作策略進行深入、實用的分析：

## 策略資訊
- **策略標題**：{strategy['title']}
- **策略類型**：{strategy['type']}
- **策略描述**：{strategy['desc']}
- **風險等級**：{strategy['risk']}
- **關注目標**：{strategy['target']}

## 分析要求

請以實戰操盤手的角度，自由發揮地提供深入分析。不需要拘泥於固定格式，請根據策略特性選擇最適合的分析角度和內容。

建議可以涵蓋（但不限於）以下面向：

1. **策略原理與逻輯** - 為什麼這個策略適合當前市場、理論基礎、歷史驗證
2. **具體執行步驟** - 進場時機、位置選擇、倉位配置、分批進場計劃
3. **風險控制與資金管理** - 停損設定、最大虧損、資金分配、對沖方法
4. **出場策略** - 獲利了結時機、停利設定、分批出場、移動停損
5. **成功關鍵與警示訊號** - 策略成功的關鍵因素、需要警惕的訊號、失敗警訊
6. **歷史案例與成功率** - 類似情況的歷史表現、成功率評估、經驗教訓
7. **適用市場條件** - 什麼市場環境下最適合、不適合的情況
8. **替代方案** - 其他可行的策略選擇、優劣勢比較

## 寫作要求
- 使用 Markdown 格式，包含清晰的標題和段落
- 提供具體的數據、價位、百分比
- 分享實戰經驗和具體案例
- 避免理論化的空洞建議
- 篇幅不限，請充分展開分析

請開始你的實戰策略分析："""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key)
    
    return {
        "strategy": strategy,
        "analysis": analysis,
        "format": "markdown",
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
    
    prompt = f"""你是一位資深的台股操盤手，擁有多年的實戰經驗和穩健的獲利紀錄。

請針對以下操作策略進行深入、實用的分析：

## 策略資訊
- **策略標題**：{strategy['title']}
- **策略類型**：{strategy['type']}
- **策略描述**：{strategy['desc']}
- **風險等級**：{strategy['risk']}
- **關注目標**：{strategy['target']}

## 分析要求

請以實戰操盤手的角度，自由發揮地提供深入分析。不需要拘泥於固定格式，請根據策略特性選擇最適合的分析角度和內容。

建議可以涵蓋（但不限於）以下面向：

1. **策略原理與逻輯** - 為什麼這個策略適合當前市場、理論基礎、歷史驗證
2. **具體執行步驟** - 進場時機、位置選擇、倉位配置、分批進場計劃
3. **風險控制與資金管理** - 停損設定、最大虧損、資金分配、對沖方法
4. **出場策略** - 獲利了結時機、停利設定、分批出場、移動停損
5. **成功關鍵與警示訊號** - 策略成功的關鍵因素、需要警惕的訊號、失敗警訊
6. **歷史案例與成功率** - 類似情況的歷史表現、成功率評估、經驗教訓
7. **適用市場條件** - 什麼市場環境下最適合、不適合的情況
8. **替代方案** - 其他可行的策略選擇、優劣勢比較

## 寫作要求
- 使用 Markdown 格式，包含清晰的標題和段落
- 提供具體的數據、價位、百分比
- 分享實戰經驗和具體案例
- 避免理論化的空洞建議
- 篇幅不限，請充分展開分析

請開始你的實戰策略分析："""

    analysis = generate_ai_analysis(prompt, api_key=x_api_key, feedback=feedback.feedback)
    
    return {
        "strategy": strategy,
        "analysis": analysis,
        "format": "markdown",
        "generated_at": datetime.now().isoformat(),
        "model": "gemini-2.5-pro",
        "regenerated": True,
        "feedback_applied": feedback.feedback
    }

class WatchlistRequest(BaseModel):
    stocks: List[str]

@app.post("/api/watchlist/events")
def get_watchlist_events(request: WatchlistRequest, x_api_key: Optional[str] = Header(None)):
    """獲取自選個股的重要事件（使用 AI 搜尋）"""
    
    if not request.stocks or len(request.stocks) == 0:
        return {"events": []}
    
    # 限制最多 10 個股票
    stocks = request.stocks[:10]
    
    # 使用 Gemini API Key
    api_key = x_api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key 未設定")
    
    try:
        client = genai.Client(api_key=api_key)
        
        # 為每個股票搜尋資訊
        all_events = []
        
        for stock in stocks:
            prompt = f"""請搜尋並提供「{stock}」這檔台股在 2026 年 1-3 月的重要事件資訊。

請以 JSON 格式輸出，包含以下欄位：

{{
  "stock": "股票代號或名稱",
  "events": [
    {{
      "date": "YYYY-MM-DD",
      "title": "事件標題",
      "type": "earnings|除權息|stockholder_meeting|conference",
      "description": "簡短描述"
    }}
  ]
}}

請只輸出 JSON，不要其他文字。如果找不到資訊，請返回空陣列。"""
            
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                    response_modalities=["TEXT"],
                )
            )
            
            result_text = response.text.strip()
            
            # 移除 markdown 格式
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            try:
                stock_data = json.loads(result_text)
                if 'events' in stock_data and isinstance(stock_data['events'], list):
                    for event in stock_data['events']:
                        # 轉換為 StockEvent 格式
                        event_type = 'corporate'
                        if event.get('type') == 'earnings':
                            event_type = 'corporate'
                        
                        all_events.append({
                            "id": f"watchlist-{stock}-{event.get('date', '')}",
                            "date": event.get('date', ''),
                            "title": f"{stock} {event.get('title', '')}",
                            "market": "TW",
                            "type": event_type,
                            "trend": "neutral",
                            "relatedStocks": [stock],
                            "description": event.get('description', ''),
                            "strategy": "關注該事件對股價的影響。"
                        })
            except json.JSONDecodeError:
                # 如果解析失敗，跳過這個股票
                continue
        
        return {"events": all_events}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋失敗: {str(e)}")

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
