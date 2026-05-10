## Auth Service for companionIO

This .NET service handles authentication for the companionIO voice assistant.

### Features
- Google OAuth2 login for users
- JWT token issuance and validation
- Role-based access (User, Admin, Agent)
- Rate limiting and audit logging
- Support for agent/service account authentication (for MCP servers, LLM, etc.)
- **Distributed & Scalable Features:**
  - Redis distributed caching for tokens
  - Health checks for monitoring
  - OpenTelemetry distributed tracing
  - Hangfire background job processing
  - Horizontal scaling ready

### Setup
1. Configure Google OAuth in Google Cloud Console
2. Update `appsettings.json` with your secrets
3. Run with `dotnet run` or build Docker image

### Endpoints
- `GET /api/auth/login` - Initiate Google login
- `GET /api/auth/callback` - OAuth callback
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/agents/register` - Register an agent (admin only)
- `POST /api/agents/authenticate` - Authenticate an agent
- `POST /api/audit/log` - Log audit events
- `GET /health` - Health check endpoint
- `GET /hangfire` - Background job dashboard (admin only)

### Scaling Architecture
- **Multiple Instances:** Deploy behind Azure Front Door or App Gateway
- **Database:** Azure PostgreSQL with read replicas
- **Cache:** Azure Cache for Redis for distributed session/token storage
- **Jobs:** Hangfire with PostgreSQL for background processing
- **Monitoring:** Application Insights + OpenTelemetry
- **Tracing:** Distributed tracing across services

### Integration with Orchestrator
- The orchestrator can call `/api/auth/me` with JWT token to get user context
- Agents can authenticate via `/api/agents/authenticate` for secure access
- Use `/health` for load balancer health check
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/agents/register` - Register an agent (admin only)
- `POST /api/agents/authenticate` - Authenticate an agent
- `POST /api/audit/log` - Log audit events
- `GET /health` - Health check endpoint
- `GET /hangfire` - Background job dashboard (admin only)

### Scaling Architecture
- **Multiple Instances:** Deploy behind Azure Front Door or App Gateway
- **Database:** Azure PostgreSQL with read replicas
- **Cache:** Azure Cache for Redis for distributed session/token storage
- **Jobs:** Hangfire with PostgreSQL for background processing
- **Monitoring:** Application Insights + OpenTelemetry
- **Tracing:** Distributed tracing across services

### Integration with Orchestrator
- The orchestrator can call `/api/auth/me` with JWT token to get user context
- Agents can authenticate via `/api/agents/authenticate` for secure access
- Use `/health` for load balancer health checks