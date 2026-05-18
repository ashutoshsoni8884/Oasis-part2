# Centralized Logging System

This document describes the production-grade logging system implemented in the Oasis FastAPI backend.

## Overview

The logging system provides comprehensive request tracing, error handling, and business event logging with the following features:

- **Request Lifecycle Tracking**: Every API request is logged with metadata, timing, and errors
- **Structured Application Logging**: Business events are logged to database for analysis
- **File Logging**: Rotating log files for persistence and debugging
- **Request Tracing**: Unique `request_id` for correlating logs across the system
- **Performance Protections**: Safe logging that never crashes the API
- **Sensitive Data Redaction**: Automatic removal of passwords, tokens, and secrets

## Architecture

### Components

1. **`logger.py`** - Centralized logger configuration
2. **`middleware/logging_middleware.py`** - FastAPI middleware for request logging
3. **`services/logging_service.py`** - Helper functions for database logging
4. **`models/logging_models.py`** - SQLAlchemy models for logging tables
5. **`middleware/exception_handlers.py`** - Global exception handlers

### Database Tables

#### `api_request_logs`
Tracks complete API request/response lifecycle:

```sql
CREATE TABLE api_request_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(36) NOT NULL,
    method VARCHAR(10) NOT NULL,
    endpoint TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    user_email VARCHAR(255),
    agent_team_code VARCHAR(100),
    request_body JSONB,
    response_body JSONB,
    error_message TEXT,
    ip_address VARCHAR(45),
    duration_ms FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `application_logs`
Structured logs for business events:

```sql
CREATE TABLE application_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(36),
    log_level VARCHAR(10) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Setup

### 1. Create Database Tables

Run the migration script:

```bash
cd Backend
python -m scripts.create_logging_tables
```

### 2. Environment Variables

Add to your `.env` file:

```bash
# Logging Configuration
ENABLE_DB_LOGGING=true
ENABLE_FILE_LOGGING=true
LOG_LEVEL=INFO
LOG_MAX_BODY_SIZE=10000
```

### 3. Automatic Integration

The logging system is automatically integrated into `main.py`:

- Logging middleware is added first
- Exception handlers catch unhandled errors
- Logger is initialized on startup

## Usage

### Request Tracing

Every request gets a unique `request_id` that appears in all related logs:

```
2024-01-15 10:30:15 | INFO | REQUEST: POST /api/chat | IP: 192.168.1.100 | User: john@example.com
2024-01-15 10:30:15 | INFO | [req_123] Intent classified | Agent: ARCREDITAGENTTEAM | Confidence: 0.95
2024-01-15 10:30:15 | INFO | [req_123] Job created: job_456 for agent ARCREDITAGENTTEAM
2024-01-15 10:30:16 | INFO | RESPONSE: 200 | Duration: 1250.50ms | Agent: ARCREDITAGENTTEAM
```

### Application Event Logging

Use `log_application_step()` for important business events:

```python
from services.logging_service import log_application_step

# In async context
await log_application_step(
    request_id, "INFO", "oracle_call",
    "Calling Oracle Fusion API",
    {"agent_team_code": "ARCREDITAGENTTEAM", "endpoint": "/api/agents"}
)

# In sync context
log_application_step_sync(
    request_id, "ERROR", "auth_failure",
    "Invalid credentials provided",
    {"username": "john@example.com"}
)
```

### Logger Usage

Replace `print()` statements with structured logging:

```python
from logger import logger, get_request_logger

# Global logger
logger.info("Application started")

# Request-scoped logger
req_logger = get_request_logger(request_id)
req_logger.error(f"[{request_id}] Database connection failed")
```

## Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about application operation
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical errors that may prevent application operation

## Security & Performance

### Data Protection

- **Redaction**: Automatically redacts sensitive fields:
  - `password`, `token`, `authorization`, `bearer_token`
  - `api_key`, `secret`, `key`, `auth`, `credential`
- **Size Limits**: Truncates large request/response bodies
- **Binary Skip**: Skips logging binary uploads

### Performance

- **Async Safe**: Database logging doesn't block API responses
- **Failure Safe**: Logging failures never crash the application
- **Caching**: Agent registry caching reduces database calls
- **Rotation**: Log files rotate at 10MB with 5 backups

## Monitoring & Analysis

### Query Examples

```sql
-- Recent API errors
SELECT * FROM api_request_logs
WHERE status_code >= 400
AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Application events by request
SELECT * FROM application_logs
WHERE request_id = 'req_123'
ORDER BY created_at;

-- Performance analysis
SELECT
    endpoint,
    AVG(duration_ms) as avg_duration,
    COUNT(*) as request_count
FROM api_request_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
ORDER BY avg_duration DESC;
```

### Log Files

Logs are written to `logs/app.log` with rotation:

```
logs/
├── app.log       # Current log file
├── app.log.1     # Previous rotation
├── app.log.2     # Older rotation
└── ...
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_DB_LOGGING` | `true` | Enable database logging |
| `ENABLE_FILE_LOGGING` | `true` | Enable file logging |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_MAX_BODY_SIZE` | `10000` | Max request/response body size |

### Advanced Configuration

Modify `logger.py` for custom formatting or additional handlers:

```python
# Add custom handler
custom_handler = logging.handlers.SysLogHandler()
logger.addHandler(custom_handler)
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check `ENABLE_FILE_LOGGING=true`
2. **Database errors**: Verify `ENABLE_DB_LOGGING=true` and DB connection
3. **Missing request_id**: Ensure middleware is added first in `main.py`
4. **Performance impact**: Monitor with `LOG_MAX_BODY_SIZE` setting

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
```

This will show detailed middleware operations and database queries.