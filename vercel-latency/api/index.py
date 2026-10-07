from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# Fixed CORS: allow_credentials MUST be False when origins is "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    regions: List[str]
    threshold_ms: float

def calc_p95(data):
    if not data: return 0
    d = sorted(data)
    idx = (len(d) - 1) * 0.95
    n = int(idx)
    l = idx - n
    if n + 1 < len(d):
        return d[n] + l * (d[n+1] - d[n])
    return float(d[n])

@app.post("/api/latency")
@app.post("/")
def get_latency(query: Query):
    try:
        # Read the file cleanly from the api folder
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'q-vercel-latency.json')
        
        with open(file_path) as f:
            raw_data = json.load(f)

        results = []
        for region in query.regions:
            region_data = [d for d in raw_data if d.get('region') == region]
            if not region_data:
                continue
            
            latencies = [d['latency_ms'] for d in region_data]
            uptimes = [d['uptime_pct'] for d in region_data]
            
            avg_lat = sum(latencies) / len(latencies)
            p95_lat = calc_p95(latencies)
            avg_up = sum(uptimes) / len(uptimes)
            breaches = sum(1 for l in latencies if l > query.threshold_ms)
            
            results.append({
                "region": region,
                "avg_latency": round(avg_lat, 2),
                "p95_latency": round(p95_lat, 2),
                "avg_uptime": round(avg_up, 3),
                "breaches": breaches
            })
        
        return {"regions": results}
    except Exception as e:
        # If anything fails, return a clean JSON error instead of crashing the server!
        return {"regions": [], "error": str(e)}