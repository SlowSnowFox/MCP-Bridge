import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from config import config
from config.final import SSEMCPServer
from .AbstractClient import GenericMcpClient
from loguru import logger


class SseClient(GenericMcpClient):
    config: SSEMCPServer

    def __init__(self, name: str, config: SSEMCPServer) -> None:
        super().__init__(name=name)

        self.config = config

    async def _maintain_session(self):
        async with sse_client(self.config.url) as client:
            async with ClientSession(*client) as session:
                await session.initialize()
                logger.debug(f"finished initialise session for {self.name}")
                self.session = session

                try:
                    while True:
                        await asyncio.sleep(10)
                        if config.logging.log_server_pings:
                            logger.debug(f"pinging session for {self.name}")

                        await session.send_ping()

                except Exception as exc:
                    logger.error(f"ping failed for {self.name}: {exc}")
                    self.session = None

        logger.debug(f"exiting session for {self.name}")
