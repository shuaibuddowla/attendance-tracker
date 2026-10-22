import socket
import uvicorn
import os
import sys

def get_local_ip():
    """Detect local LAN IP address to provide clear ESP32 target address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable, just initiates socket routing
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000

    print("=" * 65)
    print("      RFID ATTENDANCE TRACKER - FASTAPI BACKEND SERVER")
    print("=" * 65)
    print(f"  * Web Dashboard:       http://localhost:{port}")
    print(f"  * LAN Dashboard:       http://{local_ip}:{port}")
    print(f"  * ESP32 API Endpoint:  http://{local_ip}:{port}/api/scan")
    print("=" * 65)
    print("  -> Put 'http://{}:8000/api/scan' in your ESP32 Arduino code!".format(local_ip))
    print("=" * 65)

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
