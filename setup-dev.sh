#!/bin/bash

# CompanionIO Local Development Setup
# This script sets up the entire development environment

set -e

echo "🚀 Setting up CompanionIO development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Create necessary directories
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/redis

# Copy environment files if they don't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Database
POSTGRES_DB=companion_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password

# Redis
REDIS_URL=redis://redis:6379

# JWT
JWT_SECRET=dev-jwt-secret-key-change-in-production
AUTH_SERVICE_URL=http://auth:5000

# Google OAuth (for development)
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-client-secret

# Azure (for deployment)
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-service-principal-id
AZURE_CLIENT_SECRET=your-service-principal-secret
AZURE_CONTAINER_REGISTRY=yourregistry.azurecr.io
AZURE_RESOURCE_GROUP=your-resource-group
EOF
    echo "✅ Created .env file"
fi

# Start services
echo "🐳 Starting development services..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database migrations (for Auth service)
echo "🗄️ Running database migrations..."
docker-compose run --rm auth dotnet ef database update

# Build all services
echo "🏗️ Building all services..."
docker-compose build

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Run health checks
echo "🏥 Running health checks..."
services=("orchestrator" "auth" "llm" "stt")
for service in "${services[@]}"; do
    if curl -f http://localhost:$(docker-compose port $service 8000 | cut -d: -f2)/health >/dev/null 2>&1; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service health check failed"
    fi
done

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📋 Service URLs:"
echo "  - Orchestrator: http://localhost:8000"
echo "  - Auth: http://localhost:5000"
echo "  - LLM: http://localhost:8001"
echo "  - STT: http://localhost:8002"
echo ""
echo "📊 Monitoring:"
echo "  - Logs: docker-compose logs -f"
echo "  - Stop: docker-compose down"
echo "  - Clean: docker-compose down -v"
echo ""
echo "🧪 Testing:"
echo "  - Run tests: docker-compose exec orchestrator pytest"
echo "  - Health check: curl http://localhost:8000/health"