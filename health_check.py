#!/usr/bin/env python3
"""
Simple health check server for App Runner
"""
import os
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_check():
    """Start a simple health check server on port 8080"""
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()

def start_streamlit():
    """Start Streamlit on port 8501"""
    subprocess.run([
        "streamlit", "run", "streamlit_app/app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ])

if __name__ == "__main__":
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=start_health_check, daemon=True)
    health_thread.start()
    
    # Wait a moment for health check to start
    time.sleep(2)
    
    # Start Streamlit
    start_streamlit() 