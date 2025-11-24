from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
import json
import os

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

# 資料檔案路徑
DATA_DIR = os.path.dirname(__file__)
EVENTS_FILE = os.path.join(DATA_DIR, "data_events.json")
HOT_TRENDS_FILE = os.path.join(DATA_DIR, "data_hot_trends.json")
STRATEGIES_FILE = os.path.join(DATA_DIR, "data_strategies.json")

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
            "strategies": "/api/strategies"
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

@app.get("/health")
def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
