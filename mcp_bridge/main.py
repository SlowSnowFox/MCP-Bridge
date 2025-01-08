from fastapi import FastAPI
from endpoints import router as endpointRouter
from mcpManagement import router as mcpRouter
from health import router as healthRouter
from mcp_server import router as mcp_server_router
from lifespan import lifespan
from openapi_tags import tags_metadata, version

app = FastAPI(
    title="MCP Bridge",
    description="A middleware application to add MCP support to openai compatible apis",
    version=version,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

app.include_router(endpointRouter)
app.include_router(mcpRouter)
app.include_router(healthRouter)
app.include_router(mcp_server_router)

if __name__ == "__main__":
    import uvicorn
    from config import config

    uvicorn.run(app, host=config.network.host, port=config.network.port)
