# utils/api_metrics.py
import time
from datetime import datetime, timezone
from threading import Lock
from db.supabase_client import supabase

metrics_cache = {}
metrics_lock = Lock()
last_flush = 0

def record_request(endpoint: str, method: str, duration_ms: float):
    key = f"{method}:{endpoint}"
    with metrics_lock:
        if key not in metrics_cache:
            metrics_cache[key] = {"count": 0, "avg_time": 0.0}
        stats = metrics_cache[key]
        stats["count"] += 1
        stats["avg_time"] = (stats["avg_time"] * (stats["count"] - 1) + duration_ms) / stats["count"]

def flush_metrics():
    global last_flush
    now = time.time()
    if now - last_flush < 3600:  # only flush once per hour
        return
    with metrics_lock:
        for key, stats in metrics_cache.items():
            method, endpoint = key.split(":", 1)
            avg_response_ms = stats["avg_time"]
            count = stats["count"]

            try:
                supabase.rpc("increment_api_usage", {
                    "v_avg_response_ms": avg_response_ms,
                    "v_count": count,
                    "v_endpoint": endpoint,
                    "v_method": method
                }).execute()
            except Exception as e:
                print(f"[warn] failed to push metrics for {endpoint}: {e}")

        metrics_cache.clear()
        last_flush = now
