# CompanionIO - Personal Assistant Platform

A scalable, secure personal assistant platform built with microservices architecture, featuring authentication, AI language models, speech processing, and real-time communication.

## 🏗️ Architecture

CompanionIO consists of four main services:

- **Orchestrator** (Python/FastAPI) - Main coordination and API gateway
- **Auth** (.NET 8) - Authentication and authorization service
- **LLM** (Python/FastAPI) - Language model integration
- **STT** (Python/FastAPI) - Speech-to-text processing

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- GitLab account (for CI/CD)
- Azure subscription (for deployment)

### Development Setup
```bash
# Clone the repository
git clone https://gitlab.com/your-org/companion.io.git
cd companion.io

# Run the development setup script
./setup-dev.sh

# Or manually with docker-compose
docker-compose up -d
```

### Services URLs (Development)
- **Orchestrator**: http://localhost:8000
- **Auth**: http://localhost:5000
- **LLM**: http://localhost:8001
- **STT**: http://localhost:8002

## 🔧 Development

### Code Quality
```bash
# Python services
pip install ruff black isort
ruff check .
black .
isort .

# .NET service
dotnet format
```

### Testing
```bash
# Unit tests
pytest

# Integration tests
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/

# Performance tests
locust --host=http://localhost:8000
```

### Building
```bash
# Build all services
docker-compose build

# Build specific service
docker build -t companion-orchestrator ./Services/Orchestrator
```

## 🚢 CI/CD Pipeline

CompanionIO uses GitLab CI/CD for comprehensive automation:

### Pipeline Stages
1. **Validate** - Code linting, formatting, and security checks
2. **Build** - Docker image creation and registry push
3. **Test** - Unit, integration, and performance testing
4. **Security** - Vulnerability scanning and dependency checks
5. **Deploy** - Staging and production deployments
6. **Cleanup** - Old image cleanup and maintenance

### Environment Variables Required
```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-service-principal-id
AZURE_CLIENT_SECRET=your-service-principal-secret
AZURE_CONTAINER_REGISTRY=yourregistry.azurecr.io
AZURE_RESOURCE_GROUP=your-resource-group

# Application Secrets
JWT_SECRET=your-jwt-secret-key
AUTH_SERVICE_URL_STAGING=http://companion-staging-auth:5000
AUTH_SERVICE_URL_PROD=http://companion-prod-auth:5000
```

### Deployment Workflow
1. **Push to feature branch** → Automatic validation
2. **Create merge request** → Full test suite execution
3. **Merge to main** → Build and push images
4. **Manual staging deploy** → Integration testing
5. **Manual production deploy** → Live deployment with health checks

### Manual Operations
- **Performance testing**: `performance_test` job
- **Rollback**: `rollback_production` job
- **Cleanup**: `cleanup_old_images` job (scheduled/manual)

## 🔒 Security

### Authentication & Authorization
- JWT-based stateless authentication
- Google OAuth 2.0 integration
- Role-based access control (RBAC)
- Secure token validation

### Security Features
- Container vulnerability scanning
- Dependency security checks
- Secret management via Azure Key Vault
- HTTPS enforcement
- CORS configuration

## 📊 Monitoring

### Health Checks
All services expose `/health` endpoints for monitoring:
```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "orchestrator"}
```

### Metrics & Alerts
- Response times and error rates
- Resource usage (CPU, memory, disk)
- Custom business metrics
- Slack/email notifications

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Centralized log aggregation
- Log retention policies

## 🧪 Testing Strategy

### Unit Tests
- Service-specific unit tests
- Mock external dependencies
- Code coverage reporting

### Integration Tests
- Cross-service communication
- Database and cache integration
- Authentication flows

### Performance Tests
- Load testing with Locust
- Stress testing scenarios
- Performance regression detection

### End-to-End Tests
- Full user journey testing
- Browser automation
- API contract validation

## 🚀 Deployment

### Azure Container Apps
- Serverless container deployment
- Auto-scaling based on traffic
- Integrated monitoring and logging
- Cost-effective for variable workloads

### Infrastructure as Code
- Azure Bicep templates
- Infrastructure versioning
- Environment-specific configurations
- Automated provisioning

### Blue-Green Deployments
- Zero-downtime deployments
- Automatic rollback on failure
- Traffic shifting capabilities
- Health-based promotion

## 📚 API Documentation

### Orchestrator API
- RESTful endpoints for session management
- WebSocket support for real-time communication
- Authentication middleware
- Rate limiting and throttling

### Auth API
- OAuth 2.0 flows
- JWT token management
- User profile management
- Role and permission management

### Service APIs
- LLM: Text generation and conversation
- STT: Audio transcription and processing

## 🤝 Contributing

### Development Workflow
1. Create feature branch from `develop`
2. Write tests for new functionality
3. Ensure code quality checks pass
4. Create merge request with description
5. Code review and approval
6. Merge to `main` after CI passes

### Code Standards
- Python: PEP 8, type hints, docstrings
- C#: Microsoft coding conventions
- Commit messages: Conventional commits
- Documentation: Inline comments and READMEs

### Pull Request Requirements
- [ ] Tests included
- [ ] Code quality checks pass
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance impact assessed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [CI/CD Guide](CI_CD_README.md)
- [API Documentation](docs/api/)
- [Deployment Guide](docs/deployment/)

### Getting Help
- Create an issue for bugs/features
- Check existing documentation
- Contact the development team

---

Built with ❤️ using FastAPI, .NET, Docker, and Azure