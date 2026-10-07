from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
def get_latency(query: Query, response: Response):
    # Force the CORS header directly on the response
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    # Read the JSON file from the exact same folder as this script
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'q-vercel-latency.json')
    
    with open(file_path) as f:
        raw_data = json.load(f)

    results = []
    for region in query.regions:
        region_data = [d for d in raw_data if d['region'] == region]
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