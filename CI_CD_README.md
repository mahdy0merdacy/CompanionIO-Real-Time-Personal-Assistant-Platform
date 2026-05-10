# CompanionIO CI/CD Pipeline Documentation

## Pipeline Overview

This GitLab CI/CD pipeline provides comprehensive automation for the CompanionIO project:

### Stages
1. **Validate** - Code quality checks (lint, format, security)
2. **Build** - Docker image creation and registry push
3. **Test** - Unit tests, integration tests, performance tests
4. **Security** - Vulnerability scanning and dependency checks
5. **Deploy** - Staging and production deployments
6. **Cleanup** - Old image cleanup and rollback capabilities

### Services Covered
- **Orchestrator** (Python/FastAPI) - Main coordination service
- **LLM** (Python/FastAPI) - Language model service
- **STT** (Python/FastAPI) - Speech-to-text service
- **Auth** (.NET) - Authentication and authorization service

## Environment Variables Required

### Azure Configuration
```bash
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-service-principal-id
AZURE_CLIENT_SECRET=your-service-principal-secret
AZURE_CONTAINER_REGISTRY=yourregistry.azurecr.io
AZURE_RESOURCE_GROUP=your-resource-group
```

### Application Secrets
```bash
JWT_SECRET=your-jwt-secret-key
AUTH_SERVICE_URL_STAGING=http://companion-staging-auth:5000
AUTH_SERVICE_URL_PROD=http://companion-prod-auth:5000
```

## Pipeline Features

### Code Quality
- **Ruff**: Python linting and code quality
- **Black**: Python code formatting
- **isort**: Import sorting
- **dotnet format**: C# code formatting

### Testing
- **pytest**: Unit testing with coverage reports
- **Integration tests**: Full stack testing with docker-compose
- **Performance testing**: Load testing with Locust
- **Coverage reporting**: Cobertura format for GitLab integration

### Security
- **Container scanning**: Clair scanner for vulnerabilities
- **Dependency scanning**: Safety checks for Python packages
- **Secret management**: Azure Key Vault integration

### Deployment
- **Staging**: Automated deployment to staging environment
- **Production**: Manual deployment with rollback capability
- **Blue-green**: Zero-downtime deployments
- **Health checks**: Automatic verification after deployment

### Monitoring
- **Health endpoints**: Service health monitoring
- **Logs**: Centralized logging with correlation IDs
- **Metrics**: Performance and error tracking
- **Alerts**: Failure notifications

## Usage

### Development Workflow
1. **Push to feature branch** → Validation runs automatically
2. **Create merge request** → Full test suite runs
3. **Merge to main** → Build and push images
4. **Manual deploy to staging** → Integration testing
5. **Manual deploy to production** → Live deployment

### Rollback Procedure
1. Go to GitLab CI/CD → Pipelines
2. Find failed deployment pipeline
3. Run "rollback_production" job manually
4. Select previous working revision

### Manual Triggers
- **Performance testing**: Run load tests on demand
- **Staging deployment**: Manual approval required
- **Production deployment**: Manual approval required
- **Cleanup**: Scheduled or manual old image removal

## Best Practices

### Branch Protection
- `main`: Protected, requires MR approval
- `develop`: Development branch
- Feature branches: Automatic validation

### Security
- Secrets stored in GitLab CI/CD variables
- No hardcoded credentials in code
- Regular dependency updates
- Security scanning on every build

### Performance
- Parallel job execution where possible
- Caching for dependencies and build artifacts
- Incremental builds for faster feedback
- Resource optimization for cost control

### Monitoring
- Pipeline success/failure alerts
- Deployment status monitoring
- Performance regression detection
- Security vulnerability notifications

## Troubleshooting

### Common Issues
- **Build failures**: Check Docker image compatibility
- **Test failures**: Verify service dependencies
- **Deploy failures**: Check Azure permissions and quotas
- **Security scans**: Update dependencies or accept risks

### Debug Mode
- Use `gitlab-ci-pipelines` for local testing
- Enable debug logging in CI variables
- Check artifact downloads for detailed logs

This pipeline ensures reliable, secure, and efficient delivery of CompanionIO from development to production.