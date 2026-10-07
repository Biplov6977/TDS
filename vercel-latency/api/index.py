from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import urllib.request
import json

app = FastAPI()

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
    # Fetch JSON directly from your GitHub repo to bypass Vercel file system issues
    urls = [
        "https://raw.githubusercontent.com/Biplov6977/TDS/main/vercel-latency/api/q-vercel-latency.json",
        "https://raw.githubusercontent.com/Biplov6977/TDS/main/vercel-latency/q-vercel-latency.json"
    ]
    raw_data = None
    for url in urls:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                raw_data = json.loads(response.read().decode())
                break
        except:
            continue
            
    if not raw_data:
        return JSONResponse(content={"error": "Failed to fetch JSON"}, status_code=500)

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
    
    # Force CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Expose-Headers": "Access-Control-Allow-Origin"
    }
    
    return JSONResponse(content={"regions": results}, headers=headers)