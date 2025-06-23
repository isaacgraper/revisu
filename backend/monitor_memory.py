import psutil
import time
import os
from datetime import datetime

def monitor_process_memory(process_name_keywords, duration_seconds=60):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing memory monitoring for {duration_seconds} seconds...")
    max_memory_mb = 0
    target_pid = None

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'uvicorn' in proc.name() and 'main:app' in ' '.join(proc.cmdline()):
            target_pid = proc.pid
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Process Uvicorn/FastAPI found: PID {target_pid}")
            break

    if target_pid is None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: Uvicorn/FastAPI process not found. Make sure it is running.")
        return None

    try:
        process = psutil.Process(target_pid)
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            current_memory_mb = process.memory_info().rss / (1024 * 1024) # RSS: Resident Set Size
            if current_memory_mb > max_memory_mb:
                max_memory_mb = current_memory_mb
            time.sleep(1)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring completed.")
        return max_memory_mb
    except psutil.NoSuchProcess:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] The Uvicorn/FastAPI process (PID {target_pid}) no longer exists.")
        return None
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] An error occurred during monitoring: {e}")
        return None

if __name__ == "__main__":
    max_mem = monitor_process_memory(
        process_name_keywords=['uvicorn', 'main:app'],
        duration_seconds=120
    )
    if max_mem is not None:
        print(f"\n--- Monitoring Results ---")
        print(f"High usage of memory: {max_mem:.2f} MB")
    else:
        print("Not possible to monitor high usage memory.")
