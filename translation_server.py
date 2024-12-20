import random
from datetime import datetime

from aiohttp import web
from loguru import logger


class TranslationServer:
    def __init__(self, completion_time: float = 10.0, error_rate: float = 0.1):
        self.start_time = None
        self.completion_time = completion_time
        self.error_rate = error_rate
        self.app = web.Application()
        self.app.router.add_get("/status", self.handle_status)
        self.logger = logger

    async def handle_status(self, request):
        if self.start_time is None:
            self.start_time = datetime.now()

        if random.random() < self.error_rate:
            self.logger.info("Returning error status")
            return web.json_response({"result": "error"})

        elapsed = (datetime.now() - self.start_time).total_seconds()

        if elapsed >= self.completion_time:
            self.logger.info("Returning completed status")
            return web.json_response({"result": "completed"})
        else:
            self.logger.info(f"Returning pending status (elapsed: {elapsed:.1f}s)")
            return web.json_response({"result": "pending"})

    async def start(self, port: int = 8080):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()
        self.logger.info(f"Server started on port {port}")
        return site
