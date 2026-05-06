# Phase 1: Docker Redis Validation Guide

This guide walks through validating Redis state externalization locally using Docker.

## Overview

**Goal**: Verify that Phase 1 code (Redis state persistence) works correctly before deploying to Kubernetes.

**What we'll test**:
- ✅ Redis connection and persistence
- ✅ Conversation history storage (LIST)
- ✅ Message queue durability (STREAM)  
- ✅ Session metadata management (HASH)
- ✅ Orchestrator + backend service integration
- ✅ State persistence across connections

**Infrastructure**:
- Redis 7 (Docker container)
- Orchestrator (local build)
- Mock STT/LLM/TTS services (Docker containers)
- All services on a shared Docker network

---

## Prerequisites

You'll need:
- Docker & Docker Compose installed
- Python 3.14+ (for test validation script)
- Terminal access

Check installation:
```bash
docker --version
docker-compose --version
python --version
```

---

## Step 1: Prepare Environment

**1a. Copy the example .env file**

```bash
cd /home/mahdousha/Projects/companion.io/Services/Orchestrator
cp .env.example .env
```

The `.env` file should look like:
```
REDIS_URL=redis://redis:6379
STT_URL=ws://stt-service:8001/stt
LLM_URL=ws://llm-service:8002/llm
TTS_URL=ws://tts-service:8003/tts
```

**1b. Verify directory structure**

```bash
ls -la ./
# Should see: docker-compose.yml, Dockerfile, requirements-phase1.txt, .env
```

---

## Step 2: Start Docker Containers

**2a. Build and start all services**

```bash
docker-compose up --build
```

This will:
1. Build the Orchestrator Docker image
2. Pull Redis 7 image
3. Pull Python 3.14-slim image
4. Start all 6 containers: redis, orchestrator, stt-service, llm-service, tts-service
5. Output logs from all services

**Expected output** (last few lines):
```
redis          | * Ready to accept connections
orchestrator   | [ORCHESTRATOR] ✅ Redis connected, ready to accept connections
stt-service    | Uvicorn running on http://0.0.0.0:8001
llm-service    | Uvicorn running on http://0.0.0.0:8002
tts-service    | Uvicorn running on http://0.0.0.0:8003
```

If you see these messages, **you can proceed to Step 3** in a new terminal.

**2b. Troubleshooting startup**

- **Port already in use**: `docker-compose down` and retry
- **Build fails**: `docker-compose build --no-cache`
- **Redis won't start**: `docker-compose logs redis`
- **Orchestrator logs show Redis error**: `docker-compose logs orchestrator`

---

## Step 3: Validate Phase 1 (In New Terminal)

**3a. Install Python test dependencies**

```bash
# Navigate to orchestrator directory
cd /home/mahdousha/Projects/companion.io/Services/Orchestrator

# Install test script dependencies
pip install redis websockets
```

**3b. Run validation script**

```bash
python test_phase1_validation.py
```

**Expected output**:
```
✅ Redis connection successful
✅ Connected to orchestrator
🔄 Testing message flow...
   Sending 1700 bytes of mock audio...
   Waiting for response (5 second timeout)...
   ...
📊 Inspecting Redis state for test-session-abc123:
  • History: 0 messages
  • Mailbox: 0-5 messages
  • Metadata: pod_id, created_at, etc...

VALIDATION COMPLETE ✅
...
```

**What this validates**:
- Redis is accessible from your machine
- Orchestrator WebSocket endpoint works
- Mock services are responding  
- State is being recorded (or will be within seconds)

---

## Step 4: Manual Redis Inspection

**4a. Open a new terminal and connect to Redis**

```bash
# Enter Redis container
docker exec -it companion-redis redis-cli

# You should see:
# 127.0.0.1:6379>
```

**4b. Explore Redis data**

```bash
# List all keys (should see history:*, mailbox:*, session:* keys)
KEYS *

# Check a specific session's history
LRANGE history:abc123 0 -1

# Check mailbox stream (replace abc123 with actual session ID)
XRANGE mailbox:abc123 - +

# Check session metadata
HGETALL session:abc123

# Get Redis stats
INFO

# Type 'exit' to quit
exit
```

---

## Step 5: Test Full Message Flow

**5a. Optional: Write a live test client**

Create `client_test.py`:

```python
import asyncio
import websockets
import json

async def test_client():
    uri = "ws://localhost:8000/ws/session"
    async with websockets.connect(uri) as ws:
        # Send mock audio
        await ws.send_bytes(b"mock_audio" * 100)
        
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=3)
            print(f"Response: {response}")
        except asyncio.TimeoutError:
            print("No immediate response (processing in background)")
        
        # Keep connection alive to see state accumulate
        await asyncio.sleep(2)

asyncio.run(test_client())
```

Run it:
```bash
python client_test.py
```

Then in Redis CLI:
```bash
KEYS *  # See new keys created
```

---

## Step 6: Inspect Logs

**6a. View orchestrator logs**

```bash
docker-compose logs orchestrator
```

Look for:
- `[ORCHESTRATOR] 🚀 Starting up...`
- `[ORCHESTRATOR] ✅ Redis connected`
- `[ORCHESTRATOR] 🎯 New connection:` (session ID)
- `[ACTOR]` messages (state operations)

**6b. View Redis logs**

```bash
docker-compose logs redis
```

Look for:
- Connection confirmations from orchestrator
- RPUSH/LRANGE operations (history)
- XADD/XREAD operations (mailbox)
- HSET operations (metadata)

**6c. View all logs**

```bash
docker-compose logs -f  # Follow mode (Ctrl+C to exit)
```

---

## Step 7: Shutdown & Cleanup

**7a. Stop containers**

```bash
docker-compose down
```

This stops all services but keeps volumes (Redis data persists).

**7b. Full cleanup (delete volumes)**

```bash
docker-compose down -v
```

This removes all data. Useful for fresh testing.

---

## Success Criteria

You've successfully validated Phase 1 if:

- ✅ All containers start without errors
- ✅ `test_phase1_validation.py` reports "✅ Redis connection successful"
- ✅ `docker-compose logs orchestrator` shows `[ORCHESTRATOR] ✅ Redis connected`
- ✅ Redis CLI shows keys: `history:*`, `mailbox:*`, `session:*`
- ✅ Message flow test completes without handshake errors
- ✅ Logs show actor state operations

---

## Understanding the Architecture

### Data Flow

```
Client (WebSocket)
  ↓ (sends audio bytes)
Orchestrator (receives in receive_loop)
  ↓ (puts in actor mailbox)
Redis STREAM (durably queues message)
  ↓ (actor pulls and processes)
Actor (STT → LLM → TTS pipeline)
  ↓ (stores transcript/response)
Redis LIST (appends to history:session_id)
  ↓ (sends output back)
Client (receives response)
```

### Redis Structures

**History (LIST)** - Conversation persistence:
- Key: `history:{session_id}`
- Type: LIST (ordered messages)
- TTL: 24 hours
- Example: `["user: hello", "assistant: hi there", "user: how are you", ...]`

**Mailbox (STREAM)** - Durable queue:
- Key: `mailbox:{session_id}`
- Type: STREAM (ordered entries with IDs)
- TTL: 24 hours
- Example: `{id: 1234, data: {type: "audio", ...}}`

**Metadata (HASH)** - Session info:
- Key: `session:{session_id}`
- Type: HASH (key-value)
- TTL: 24 hours
- Example: `{pod_id: "orch-1", created_at: "2024-04-27", status: "active"}`

---

## Next: Phase 2 (Kubernetes)

Once Phase 1 validation is complete:

1. **Create Dockerfile** for each service (STT, LLM, TTS)
   - Use orchestrator's Dockerfile as template
   
2. **Create Kubernetes manifests**:
   - Deployment for orchestrator (3 replicas)
   - Service for orchestrator (LoadBalancer/Ingress)
   - StatefulSet or use DigitalOcean Managed Redis
   - ConfigMap for environment variables
   - Secrets for Redis auth (production)

3. **Use docker-compose as local K8s simulation**:
   - Same environment variables
   - Same service names (Docker network ↔ K8s DNS names)
   - Same data paths (volumes ↔ PersistentVolumes)

4. **Deploy to DigitalOcean**:
   - Create DOKS (Kubernetes cluster)
   - Push images to Docker Hub / GitHub Container Registry
   - Apply K8s manifests
   - Configure Ingress NGINX
   - Setup auth (Phase 2.5)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker-compose: command not found` | Install Docker Desktop or `apt install docker-compose` |
| Port 6379 already in use | Kill process: `lsof -i :6379` then `kill -9 <PID>` |
| Build fails | `docker system prune` then `docker-compose build --no-cache` |
| Can't connect to orchestrator | Check: `docker-compose ps` (is it running?) |
| Redis keys aren't persisting | Check volume: `docker volume ls` and `docker volume inspect` |
| Logs are hard to read | Use: `docker-compose logs orchestrator \| grep ERROR` |

---

## Key Files

- `docker-compose.yml` - Defines all 6 services and their configuration
- `Dockerfile` - Build image for orchestrator
- `mock_services/*.py` - Minimal STT/LLM/TTS implementations
- `test_phase1_validation.py` - Automated validation script
- `.env` - Environment variables (create from `.env.example`)

---

## Questions?

Check:
1. Docker Compose logs: `docker-compose logs <service>`
2. Redis data: `docker exec companion-redis redis-cli KEYS '*'`
3. Orchestrator health: `curl http://localhost:8000/health`

Good luck! 🚀
