import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from fastapi import FastAPI, Request, status
import google.auth
from google.auth.transport import requests
import uvicorn
import httpx
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

PROJECT_ID = "1234"


class TokenManager:
    def __init__(self):
        self.creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.auth_req = requests.Request()
        self.last_refresh = None

    async def get_token(self):
        if self.last_refresh is None or datetime.now() - self.last_refresh > timedelta(
            minutes=55
        ):
            self.creds.refresh(self.auth_req)
            self.last_refresh = datetime.now()
        return self.creds.token


token_manager = TokenManager()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    try:
        _ = await token_manager.get_token()
        return {"status": "healthy", "token": "valid"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }, status.HTTP_500_INTERNAL_SERVER_ERROR


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    token = await token_manager.get_token()

    async with httpx.AsyncClient() as client:
        url = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/us-central1/endpoints/openapi/{path}"

        body = await request.body()
        headers = {"Authorization": f"Bearer {token}"}

        stream = False
        if request.method in ["POST", "PUT"] and body:
            try:
                request_json = await request.json()
                stream = request_json.get("stream", False)
            except json.JSONDecodeError:
                pass

        if stream:
            async with client.stream(
                method=request.method, url=url, headers=headers, content=body
            ) as response:

                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk

                return StreamingResponse(generate(), media_type="text/event-stream")

        response = await client.request(
            method=request.method, url=url, headers=headers, content=body
        )

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON: {e}")
                return {"error": "Invalid JSON response from upstream server"}

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
