import asyncio
import websockets

async def test():
    async with websockets.connect("ws://127.0.0.1:8000/llm") as ws:
        await ws.send("hello")

        while True:
            msg = await ws.recv()
            print(msg, end="")

asyncio.run(test())