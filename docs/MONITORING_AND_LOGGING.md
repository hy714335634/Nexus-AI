# Monitoring and Logging Guide

This guide covers monitoring, logging, and observability for the Nexus-AI Platform API.

## Table of Contents

- [Health Check Endpoints](#health-check-endpoints)
- [Logging Configuration](#logging-configuration)
- [Metrics Collection](#metrics-collection)
- [Alerting](#alerting)
- [Performance Monitoring](#performance-monitoring)
- [Troubleshooting](#troubleshooting)

## Health Check Endpoints

The API provides multiple health check endpoints for different use cases:

### Basic Health Check

**Endpoint:** `GET /health`

Use this for basic load balancer health checks.

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00.000000Z"
  }
}
```

### Detailed Health Check

**Endpoint:** `GET /health/detailed`

Provides comprehensive health information including database connectivity, AWS configuration, and system metrics.

```bash
curl http://localhost:8000/health/detailed
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00.000000Z",
    "checks": {
      "database": {
        "status": "healthy",
        "message": "DynamoDB connection successful"
      },
      "aws_credentials": {
        "status": "configured",
        "message": "AWS credentials configured"
      }
    },
    "system": {
      "cpu_percent": 15.2,
      "memory_percent": 45.8,
      "process_memory_mb": 256.5,
      "uptime_seconds": 3600
    }
  }
}
```

### Kubernetes/Container Health Checks

#### Readiness Check

**Endpoint:** `GET /health/ready`

Returns 200 when the service is ready to accept traffic, 503 otherwise.

```yaml
# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

#### Liveness Check

**Endpoint:** `GET /health/live`

Returns 200 if the process is alive.

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

## Logging Configuration

### Log Levels

The API uses Python's standard logging levels:

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages for unexpected but handled situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors that may cause service disruption

### Configure Log Level

Set the log level via environment variable:

```bash
export LOG_LEVEL=INFO
```

Or in `.env` file:

```env
LOG_LEVEL=INFO
```

### Log Format

Logs are formatted as JSON for easy parsing:

```json
{
  "timestamp": "2024-01-01T12:00:00.000000Z",
  "level": "INFO",
  "logger": "api.services.project_service",
  "message": "Project created successfully",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "proj_abc123",
  "user_id": "user_123"
}
```

### Log Files

Logs are written to the following locations:

- **Development:** `logs/api.log`
- **Production:**
  - Access logs: `logs/access.log`
  - Error logs: `logs/error.log`

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Install logrotate
sudo apt-get install logrotate

# Create logrotate config
sudo nano /etc/logrotate.d/nexus-ai
```

**logrotate configuration:**

```
/path/to/nexus-ai/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload nexus-ai || true
    endscript
}
```

### Viewing Logs

#### Tail logs in real-time

```bash
# Development
tail -f logs/api.log

# Production
tail -f logs/error.log logs/access.log

# Using deployment script
./scripts/deploy.sh logs
```

#### Search logs

```bash
# Search for errors
grep "ERROR" logs/api.log

# Search by request ID
grep "550e8400-e29b-41d4-a716-446655440000" logs/api.log

# Search by project ID
grep "proj_abc123" logs/api.log
```

#### Parse JSON logs

```bash
# Extract error messages
cat logs/api.log | jq 'select(.level == "ERROR") | .message'

# Group by logger
cat logs/api.log | jq -r '.logger' | sort | uniq -c

# Filter by timestamp
cat logs/api.log | jq 'select(.timestamp > "2024-01-01T00:00:00Z")'
```

## Metrics Collection

### API Metrics

The API exposes the following metrics via the `/health/detailed` endpoint:

- **System Metrics:**
  - CPU usage percentage
  - Memory usage percentage
  - Process memory usage (MB)
  - Service uptime (seconds)

- **Database Metrics:**
  - Connection status
  - Query success/failure rates

### Business Metrics

Available via the Statistics API (`/api/v1/statistics/overview`):

- Total agents (by status)
- Total builds
- Build success rate
- Average build time
- Daily API calls

### Prometheus Integration (Optional)

To integrate with Prometheus, install the prometheus-fastapi-instrumentator:

```bash
pip install prometheus-fastapi-instrumentator
```

**Update `api/main.py`:**

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Add after app creation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: 'nexus-ai-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Import the provided Grafana dashboard template to visualize metrics:

1. Navigate to Grafana
2. Click "+" → "Import"
3. Upload `monitoring/grafana-dashboard.json`
4. Select Prometheus data source
5. Click "Import"

Key dashboard panels:
- Request rate
- Response time (p50, p95, p99)
- Error rate
- Active builds
- Agent invocations

## Alerting

### Alert Rules

Configure alerts for critical conditions:

#### High Error Rate

```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
for: 5m
labels:
  severity: critical
annotations:
  summary: "High error rate detected"
  description: "Error rate is {{ $value }} requests/second"
```

#### High Memory Usage

```yaml
alert: HighMemoryUsage
expr: process_memory_percent > 80
for: 10m
labels:
  severity: warning
annotations:
  summary: "High memory usage detected"
  description: "Memory usage is {{ $value }}%"
```

#### Database Connection Failure

```yaml
alert: DatabaseConnectionFailure
expr: up{job="nexus-ai-api"} == 0
for: 2m
labels:
  severity: critical
annotations:
  summary: "Database connection lost"
  description: "Cannot connect to DynamoDB"
```

#### Build Failure Rate

```yaml
alert: HighBuildFailureRate
expr: build_success_rate < 70
for: 1h
labels:
  severity: warning
annotations:
  summary: "High build failure rate"
  description: "Build success rate is {{ $value }}%"
```

### Notification Channels

Configure notification channels for alerts:

- **Email:** Send alerts to ops team
- **Slack:** Post to #alerts channel
- **PagerDuty:** For critical production issues
- **SMS:** For urgent critical alerts

## Performance Monitoring

### Request Tracing

Enable request tracing to track request flow:

```python
# api/middleware/tracing.py
from fastapi import Request
import uuid
import time

@app.middleware("http")
async def add_tracing(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = str(duration)

    logger.info(
        f"Request completed",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_seconds": duration
        }
    )

    return response
```

### Slow Query Detection

Log slow database queries:

```python
# api/database/dynamodb_client.py
import time

def query_with_timing(self, *args, **kwargs):
    start_time = time.time()
    result = self.query(*args, **kwargs)
    duration = time.time() - start_time

    if duration > 1.0:  # Log queries over 1 second
        logger.warning(
            f"Slow query detected: {duration:.2f}s",
            extra={"duration_seconds": duration, "operation": "query"}
        )

    return result
```

### Memory Profiling

Profile memory usage with memory_profiler:

```bash
# Install memory_profiler
pip install memory_profiler

# Run with profiling
python -m memory_profiler api/main.py
```

### Performance Benchmarking

Use locust for load testing:

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host http://localhost:8000
```

**Example locustfile.py:**

```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_projects(self):
        self.client.get("/api/v1/projects")

    @task(2)
    def get_project(self):
        self.client.get("/api/v1/projects/proj_123")

    @task(1)
    def get_statistics(self):
        self.client.get("/api/v1/statistics/overview")
```

## Troubleshooting

### Common Issues

#### 1. High CPU Usage

**Symptoms:** CPU usage consistently above 80%

**Diagnosis:**

```bash
# Check process CPU usage
top -p $(cat api.pid)

# Check API health
curl http://localhost:8000/health/detailed
```

**Solutions:**

- Scale horizontally (add more instances)
- Optimize database queries
- Enable caching
- Profile CPU-intensive operations

#### 2. Memory Leaks

**Symptoms:** Memory usage continuously increasing

**Diagnosis:**

```bash
# Monitor memory over time
watch -n 5 'curl -s http://localhost:8000/health/detailed | jq .data.system.process_memory_mb'

# Check for memory leaks
python -m memory_profiler api/main.py
```

**Solutions:**

- Check for unclosed connections
- Review large object allocations
- Enable garbage collection logging
- Restart service periodically

#### 3. Database Connection Errors

**Symptoms:** 500 errors with database connection failures

**Diagnosis:**

```bash
# Check database health
curl http://localhost:8000/health/detailed | jq .data.checks.database

# Test AWS credentials
aws dynamodb list-tables --region us-east-1
```

**Solutions:**

- Verify AWS credentials
- Check network connectivity
- Verify DynamoDB table exists
- Check IAM permissions

#### 4. Slow Response Times

**Symptoms:** Response times above 5 seconds

**Diagnosis:**

```bash
# Measure response time
time curl http://localhost:8000/api/v1/projects

# Check system load
uptime

# Review slow queries in logs
grep "Slow query" logs/api.log
```

**Solutions:**

- Add database indexes
- Implement caching (Redis)
- Optimize query patterns
- Use pagination for large result sets

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart API
./scripts/deploy.sh restart
```

**Note:** Never enable debug mode in production as it may expose sensitive information.

### Request Tracing

Trace specific requests using the request ID:

```bash
# Find all logs for a specific request
grep "550e8400-e29b-41d4-a716-446655440000" logs/api.log

# Extract trace
cat logs/api.log | jq 'select(.request_id == "550e8400-e29b-41d4-a716-446655440000")'
```

### Performance Profiling

Profile API endpoints:

```bash
# Install cProfile
pip install cprofilev

# Run with profiling
python -m cProfile -o profile.stats api/main.py

# Visualize results
cprofilev profile.stats
```

## Best Practices

1. **Always use structured logging** with JSON format for easy parsing
2. **Include request IDs** in all logs for tracing
3. **Set up log rotation** to prevent disk space issues
4. **Monitor key metrics** continuously (error rate, response time, memory)
5. **Configure alerts** for critical conditions
6. **Use health checks** in load balancers and orchestrators
7. **Review logs regularly** for patterns and anomalies
8. **Test alerting** to ensure notifications work correctly
9. **Document runbooks** for common issues
10. **Perform regular load testing** to identify bottlenecks

## Resources

- [FastAPI Logging](https://fastapi.tiangolo.com/advanced/middleware/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Grafana Documentation](https://grafana.com/docs/)
