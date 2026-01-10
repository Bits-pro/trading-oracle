"""
Gunicorn configuration for production deployment
"""
import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000

# Timeouts
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "/var/log/trading-oracle/gunicorn-access.log"
errorlog = "/var/log/trading-oracle/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "trading_oracle"

# Server mechanics
daemon = False
pidfile = "/var/run/trading-oracle.pid"
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Development/Debug
reload = False
preload_app = True
