import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from core.supervisor import SessionSupervisor



supervisor=SessionSupervisor()

@asynccontextmanager
async def lifespan(app:FastAPI):
    yield #supervisor stateless at startup, actors spawn on connection
    #ki tsir shutdown tsaker l active sessions lkol
    for sid in list(supervisor._actors.keys()):
        await supervisor.terminate(sid)

app=FastAPI(lifespan=lifespan)


@app.websocket("/ws/session")
async def session_endpoint(ws:WebSocket):
    await ws.accept()
    session_id=str(uuid.uuid4())
    actor= await supervisor.spawn(session_id)




    #two concurrent tasks: tekhou audio ml client, yrajaalou transcript

    async def receive_loop():
        try:
            while True:
                audio=await ws.receive_bytes()
                await actor.send({"type":"audio","data":audio})
        except WebSocketDisconnect:
            print("[ORCHESTRATOR] Client disconnected, signaling actor to close session")
            await actor.send({"type":"stop"})
        except Exception as e:
            print(f"[ORCHESTRATOR] Receive loop error: {e}")
            await actor.send({"type":"stop"})
    
    async def send_loop():
        try:
            while True:
                msg=await actor.recv()
                print(f"[ORCHESTRATOR] Sending to client: {msg['data']}")
                try:
                    if msg["type"]=="transcript":
                        await ws.send_text(f"TRANSCRIPT: {msg['data']}")
                    elif msg["type"]=="token":
                        await ws.send_text(msg["data"])
                    elif msg["type"]=="audio":
                        await ws.send_bytes(msg["data"])
                    elif msg["type"]=="turn_end":
                        await ws.send_text("__TURN_END__")
                        pass  # Exit after turn_end successfully sent
                except Exception as e:
                    print(f"[ORCHESTRATOR] Failed to send message: {e}, continuing...")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ORCHESTRATOR] Send loop error: {e}")
    
    receive_task= asyncio.create_task(receive_loop())
    send_task=asyncio.create_task(send_loop())

    try:
        await asyncio.gather(receive_task,send_task)
    except Exception:
        pass
    finally:
        receive_task.cancel()
        send_task.cancel()
        await supervisor.terminate(session_id)


