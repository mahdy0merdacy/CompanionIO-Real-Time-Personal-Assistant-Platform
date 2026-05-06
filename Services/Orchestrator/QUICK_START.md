# Quick Start: Docker Redis Validation

## TL;DR - Run These Commands

Terminal 1:
```bash
cd /home/mahdousha/Projects/companion.io/Services/Orchestrator
cp .env.example .env
docker-compose up --build
```

Terminal 2 (wait for "Ready to accept connections"):
```bash
cd /home/mahdousha/Projects/companion.io/Services/Orchestrator
pip install redis websockets
python test_phase1_validation.py
```

Terminal 3 (optional - inspect Redis):
```bash
docker exec -it companion-redis redis-cli
KEYS *
LRANGE history:test-session-* 0 -1
exit
```

---

## What Should Happen

**Terminal 1** shows:
- Redis ready
- Orchestrator connected to Redis ✅
- Mock services responding

**Terminal 2** shows:
- ✅ Redis connection successful
- ✅ Connected to orchestrator
- `VALIDATION COMPLETE ✅`

**Terminal 3** shows:
- Keys like: `history:test-session-abc`, `mailbox:test-session-abc`, etc.

---

## Cleanup

```bash
docker-compose down -v  # Remove everything
```

---

Done! Ready for Phase 2 (Kubernetes).
