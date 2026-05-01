import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from core.supervisor import SessionSupervisor


supervisor = SessionSupervisor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for sid in list(supervisor._actors.keys()):
        await supervisor.terminate(sid)

app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/session")
async def session_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())
    actor = await supervisor.spawn(session_id)

    async def receive_loop():
        try:
            while True:
                audio = await ws.receive_bytes()
                await actor.send({"type": "audio", "data": audio})
        except WebSocketDisconnect:
            print("[ORCHESTRATOR] Client disconnected, signaling actor to close session")
            await actor.send({"type": "stop"})
        except Exception as e:
            print(f"[ORCHESTRATOR] Receive loop error: {e}")
            await actor.send({"type": "stop"})

    async def send_loop():
        current_turn_text = ""  # accumule les tokens LLM pour le TTS

        try:
            while True:
                msg = await actor.recv()
                msg_type = msg.get("type")
                msg_data = msg.get("data", "")

                print(f"[ORCHESTRATOR] Sending to client: type={msg_type}")

                try:
                    if msg_type == "transcript":
                        current_turn_text = ""  # reset pour nouveau turn
                        await ws.send_text(f"TRANSCRIPT: {msg_data}")

                    elif msg_type == "token":
                        current_turn_text += msg_data
                        await ws.send_text(msg_data)

                    # ✅ FIX: l'actor envoie "turn_complete", pas "turn_end"
                    elif msg_type in ("turn_end", "turn_complete"):
                        await ws.send_text("__TURN_END__")
                        # Lance le TTS en arrière-plan
                        if current_turn_text.strip():
                            print(f"[TTS CLIENT] Lancement TTS pour : {current_turn_text[:60]}...")
                            asyncio.create_task(
                                _stream_tts_to_client(ws, current_turn_text)
                            )
                        current_turn_text = ""

                    elif msg_type == "stop":
                        print("[ORCHESTRATOR] Actor stopped, closing send loop")
                        break

                except Exception as e:
                    print(f"[ORCHESTRATOR] Failed to send message: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ORCHESTRATOR] Send loop error: {e}")

    receive_task = asyncio.create_task(receive_loop())
    send_task = asyncio.create_task(send_loop())

    try:
        await asyncio.gather(receive_task, send_task)
    except Exception:
        pass
    finally:
        receive_task.cancel()
        send_task.cancel()
        await supervisor.terminate(session_id)


async def _stream_tts_to_client(ws: WebSocket, text: str):
    """Connecte au TTS, reçoit les chunks audio PCM16, les envoie au frontend."""
    import websockets

    tts_url = "ws://127.0.0.1:8003/tts"

    try:
        async with websockets.connect(tts_url) as tts_ws:
            print(f"[TTS CLIENT] ✅ Connecté au TTS")
            await tts_ws.send(text)

            await ws.send_text("__AUDIO_START__")
            print(f"[TTS CLIENT] 🔊 __AUDIO_START__ envoyé au frontend")

            chunk_count = 0
            async for chunk in tts_ws:
                if isinstance(chunk, bytes):
                    await ws.send_bytes(chunk)
                    chunk_count += 1

            await ws.send_text("__AUDIO_END__")
            print(f"[TTS CLIENT] ✅ __AUDIO_END__ envoyé — {chunk_count} chunks audio transmis")

    except Exception as e:
        print(f"[TTS CLIENT] ❌ Erreur: {e}")
        try:
            await ws.send_text("__AUDIO_END__")
        except Exception:
            pass
