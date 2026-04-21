import asyncio

class Mailbox:
    """
    Thin wrapper around asyncio.Queue.
    This is the ONLY file that changes when we migrate to Redis Streams.
    The actor never imports asyncio.Queue directly — always goes through here.
    """
    def __init__(self):
        self._q = asyncio.Queue()

    async def enqueue(self, msg: dict):
        await self._q.put(msg)

    async def dequeue(self) -> dict:
        return await self._q.get()

    def empty(self) -> bool:
        return self._q.empty()