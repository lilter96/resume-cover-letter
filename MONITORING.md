# Resume Generator - Production Monitoring Guide

## Overview

This document describes the comprehensive production monitoring system implemented for the Resume Generator application. The system includes metrics collection, alerting, logging, and visualization using industry-standard tools.

## Architecture

### Components

1. **Prometheus** - Metrics collection and storage
2. **Grafana** - Visualization and dashboards
3. **Loki** - Log aggregation
4. **Promtail** - Log collection agent
5. **AlertManager** - Alert handling and notifications
6. **Node Exporter** - System metrics
7. **cAdvisor** - Container metrics

### Metrics Collection

The application collects comprehensive metrics including:

#### Business Metrics
- **Daily Active Users (DAU)** - Users who generated documents today
- **Weekly Active Users (WAU)** - Users active in the last 7 days
- **Monthly Active Users (MAU)** - Users active in the last 30 days
- **Total Revenue** - Sum of all successful payments
- **Conversion Rate** - Percentage of users who made payments
- **Average Revenue Per User (ARPU)** - Total revenue divided by total users
- **Document Generations** - Total and daily generation counts

#### Technical Metrics
- **HTTP Request Rate** - Requests per second by endpoint
- **HTTP Response Time** - Response time percentiles (50th, 95th, 99th)
- **Error Rate** - Application errors per second
- **LLM API Usage** - Request rate, response time, token usage, costs
- **Document Generation Time** - Time taken to generate documents

#### LLM Metrics
- **Request Count** - Total LLM API requests by model and type
- **Token Usage** - Total tokens consumed by model and type
- **Cost Tracking** - Estimated costs in USD
- **Response Time** - LLM API response times
- **Success Rate** - Successful vs failed LLM requests

#### Payment Metrics
- **Payment Success Rate** - Successful payments by method
- **Payment Processing Time** - Time to process payments
- **Revenue by Payment Method** - Breakdown of revenue sources
- **Failed Payments** - Count and rate of payment failures

#### Credit System Metrics
- **Credits Issued** - Total credits issued by source (purchase, bonus)
- **Credits Used** - Total credits consumed by user type
- **Credit Balance** - Total credits across all users

## Setup Instructions

### 1. Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for monitoring stack
- Ports 3000, 8080, 9090, 9093, 9100, 3100 available

### 2. Start Monitoring Stack

```bash
# Make startup script executable
chmod +x start_monitoring.sh

# Start all monitoring services
./start_monitoring.sh
```

### 3. Install Application Dependencies

```bash
# Install Python dependencies including monitoring libraries
pip install -r requirements.txt
```

### 4. Start Application with Monitoring

```bash
# Start the application with metrics enabled
python app.py
```

## Access Points

### Grafana Dashboards
- **URL**: http://localhost:3000
- **Login**: admin / admin123
- **Dashboards**:
  - Resume Generator - Business Metrics
  - Resume Generator - Technical Metrics

### Prometheus
- **URL**: http://localhost:9090
- **Use**: Query metrics, view targets, check alerts

### AlertManager
- **URL**: http://localhost:9093
- **Use**: View active alerts, configure notifications

### Application Metrics
- **URL**: http://localhost:8000/metrics
- **Use**: Prometheus metrics endpoint

## Key Metrics and Queries

### Business KPIs

```promql
# Daily Active Users
resume_generator_users_active_daily

# Revenue Growth Rate
rate(resume_generator_revenue_usd_total[24h])

# Conversion Rate
resume_generator_conversion_rate

# LLM Cost Efficiency
rate(resume_generator_llm_cost_usd_total[1h]) / rate(resume_generator_generations_total[1h])
```

### Technical Performance

```promql
# 95th Percentile Response Time
histogram_quantile(0.95, rate(resume_generator_http_request_duration_seconds_bucket[5m]))

# Error Rate
rate(resume_generator_errors_total[5m])

# LLM API Success Rate
rate(resume_generator_llm_requests_total{status="success"}[5m]) / rate(resume_generator_llm_requests_total[5m])
```

## Alerting Rules

### Critical Alerts
- **Application Down** - Application unreachable for >1 minute
- **High Error Rate** - Error rate >10% for >2 minutes
- **LLM API Failures** - LLM failure rate >5% for >1 minute
- **Payment Failures** - Payment failure rate >1% for >2 minutes

### Warning Alerts
- **High Response Time** - 95th percentile >5 seconds for >3 minutes
- **High LLM Costs** - LLM costs >$10/hour
- **High CPU/Memory Usage** - System resources >80% for >5 minutes

### Info Alerts
- **Low Daily Active Users** - DAU <5 for >30 minutes
- **Low Credit Balance** - System credits <100

## Log Management

### Log Types
- **Application Logs** - General application events
- **Access Logs** - HTTP request logs in Apache format
- **Error Logs** - Application errors and exceptions
- **Structured Logs** - JSON-formatted logs for parsing

### Log Locations
- **Application**: `logs/app.log`
- **Access**: `logs/access.log`
- **Errors**: `logs/error.log`

### Loki Queries

```logql
# Application errors
{job="resume-generator"} |= "ERROR"

# Slow requests
{job="resume-generator"} | json | duration > 5

# User activity
{job="resume-generator"} | json | user_id != ""
```

## Dashboard Descriptions

### Business Metrics Dashboard

1. **Active Users Panel** - DAU, WAU, MAU trends
2. **Revenue Panel** - Total revenue with growth indicators
3. **Document Generations** - Daily generation counts and rates
4. **LLM Costs** - Total and trending LLM expenses
5. **Revenue by Payment Method** - Pie chart of payment sources
6. **Conversion Rate** - User to customer conversion percentage
7. **ARPU** - Average revenue per user
8. **System Stats** - Total users and credit balance

### Technical Metrics Dashboard

1. **HTTP Request Rate** - Requests per second by endpoint
2. **Response Time** - Percentile-based response times
3. **LLM Request Rate** - LLM API usage patterns
4. **LLM Response Time** - LLM API performance
5. **Error Rate** - Application error trends
6. **Generation Time** - Document generation performance

## Maintenance

### Daily Tasks
- Check Grafana dashboards for anomalies
- Review AlertManager for active alerts
- Monitor disk usage for log storage

### Weekly Tasks
- Review LLM cost trends
- Analyze user growth patterns
- Check system resource usage

### Monthly Tasks
- Archive old logs
- Review and update alert thresholds
- Analyze business metrics trends

## Troubleshooting

### Common Issues

1. **Metrics Not Appearing**
   - Check application is running on port 8000
   - Verify `/metrics` endpoint is accessible
   - Check Prometheus targets in web UI

2. **Grafana Dashboard Empty**
   - Verify Prometheus datasource connection
   - Check metric names in queries
   - Ensure time range includes data

3. **Alerts Not Firing**
   - Check AlertManager configuration
   - Verify alert rules syntax
   - Test notification channels

4. **High Resource Usage**
   - Adjust retention periods
   - Optimize query frequency
   - Scale monitoring infrastructure

### Log Analysis

```bash
# View recent application logs
tail -f logs/app.log

# Search for errors
grep "ERROR" logs/app.log

# Monitor access patterns
tail -f logs/access.log | grep "POST"
```

## Security Considerations

- Grafana admin password should be changed from default
- AlertManager webhook URLs should be secured
- Metrics endpoint can be restricted to internal networks
- Log files may contain sensitive information

## Performance Impact

The monitoring system is designed to have minimal impact:
- Metrics collection: <1ms per request
- Memory overhead: ~50MB
- CPU overhead: <2%
- Storage: ~100MB/day for metrics and logs

## Scaling

For high-traffic deployments:
- Use external Prometheus with clustering
- Implement log rotation and archival
- Consider metrics sampling for high-volume endpoints
- Use dedicated monitoring infrastructure

## Integration with CI/CD

The monitoring system can be integrated with deployment pipelines:
- Health checks before deployment
- Automated rollback on alert conditions
- Performance regression detection
- Deployment success metrics

## Support

For issues with the monitoring system:
1. Check service logs: `docker-compose logs -f`
2. Verify configuration files
3. Review Prometheus targets and rules
4. Test alert notification channels