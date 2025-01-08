import asyncio
from mcp import ClientSession, StdioServerParameters, stdio_client

from config import config
from .AbstractClient import GenericMcpClient
from loguru import logger
import shutil
import os


class StdioClient(GenericMcpClient):
    config: StdioServerParameters

    def __init__(self, name: str, config: StdioServerParameters) -> None:
        super().__init__(name=name)

        env = dict(os.environ.copy())

        if config.env is not None:
            env.update(config.env)

        command = shutil.which(config.command)
        if command is None:
            logger.error(f"could not find command {config.command}")
            exit(1)

        own_config = config.model_copy(deep=True)

        # this changes the default to ignore
        if "encoding_error_handler" not in config.model_fields_set:
            own_config.encoding_error_handler = "ignore"

        self.config = own_config

    async def _maintain_session(self):
        async with stdio_client(self.config) as client:
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
