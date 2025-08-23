#!/bin/bash

# Resume Generator - Production Monitoring Stack Startup Script
# This script starts Prometheus, Grafana, Loki, and related monitoring services

set -e

echo "🚀 Starting Resume Generator Monitoring Stack"
echo "=============================================="

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p monitoring/data/{prometheus,grafana,loki,alertmanager}

# Set permissions
chmod 755 logs
chmod -R 755 monitoring/

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Stop any existing monitoring stack
echo "🛑 Stopping existing monitoring stack..."
docker-compose -f docker-compose.monitoring.yml down --remove-orphans 2>/dev/null || true

# Pull latest images
echo "📥 Pulling latest monitoring images..."
docker-compose -f docker-compose.monitoring.yml pull

# Start monitoring stack
echo "🔄 Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✅ Prometheus is healthy (http://localhost:9090)"
else
    echo "❌ Prometheus is not responding"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is healthy (http://localhost:3000)"
    echo "   Default login: admin/admin123"
else
    echo "❌ Grafana is not responding"
fi

# Check Loki
if curl -s http://localhost:3100/ready > /dev/null; then
    echo "✅ Loki is healthy (http://localhost:3100)"
else
    echo "❌ Loki is not responding"
fi

# Check AlertManager
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "✅ AlertManager is healthy (http://localhost:9093)"
else
    echo "❌ AlertManager is not responding"
fi

echo ""
echo "🎉 Monitoring Stack Started Successfully!"
echo "========================================="
echo ""
echo "📊 Access Points:"
echo "  • Grafana Dashboard: http://localhost:3000 (admin/admin123)"
echo "  • Prometheus: http://localhost:9090"
echo "  • AlertManager: http://localhost:9093"
echo "  • Loki: http://localhost:3100"
echo ""
echo "📈 Available Dashboards:"
echo "  • Business Metrics: Resume Generator - Business Metrics"
echo "  • Technical Metrics: Resume Generator - Technical Metrics"
echo ""
echo "🔧 Next Steps:"
echo "  1. Start your Resume Generator application with metrics enabled"
echo "  2. Visit Grafana to view dashboards"
echo "  3. Configure alert notifications in AlertManager"
echo ""
echo "📝 Logs are stored in:"
echo "  • Application logs: ./logs/"
echo "  • Container logs: docker-compose logs -f"
echo ""
echo "🛑 To stop monitoring: docker-compose -f docker-compose.monitoring.yml down"