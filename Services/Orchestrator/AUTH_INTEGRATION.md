## Auth Integration for Orchestrator

### Stateless Authentication

The orchestrator maintains statelessness by:

1. **JWT-Only Validation**: Tokens are validated locally using PyJWT
2. **No Session Storage**: User state lives in Redis (external)
3. **Optional Auth Service Calls**: User info fetched only when needed
4. **Token Refresh Proxy**: Forwards refresh requests to auth service

### Security Flow

```
Client Request → JWT Middleware → Validate Token → Extract User Context → Process Request
                      ↓
               Token Expired? → Return 401
                      ↓
             Need User Info? → Call Auth Service (cached)
```

### Environment Variables

```bash
JWT_SECRET="your-secret-key"
AUTH_SERVICE_URL="http://auth-service:5000"
```

### Usage Examples

**Protected Endpoint:**
```python
@app.get("/api/sessions")
async def get_sessions(user: dict = Depends(get_user_context)):
    return {"user": user["email"], "sessions": []}
```

**Role-Based Access:**
```python
@app.get("/admin/users")
async def admin_only(user: dict = Depends(require_admin)):
    return {"message": "Admin access granted"}
```

**WebSocket with Auth:**
```python
@router.websocket("/session/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str, user: dict = Depends(get_user_context)):
    # Authenticated WebSocket connection
    pass
```

### Scaling Benefits

- **No Auth Service Dependency**: Can validate tokens offline
- **Horizontal Scaling**: Multiple instances share no state
- **Performance**: Local JWT validation (fast)
- **Resilience**: Auth service can be down for token validation

### Integration with Other Services

Apply the same pattern to LLM, STT, and client services:

1. Add JWT validation middleware
2. Extract user context from tokens
3. Use role-based authorization
4. Keep services stateless