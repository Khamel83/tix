import httpx
import logging
from ticket_sniper.config import settings
from ticket_sniper.argus.models import FetchRawRequest, FetchRawResponse

logger = logging.getLogger(__name__)

class ArgusClient:
    def __init__(self):
        self.base_url = settings.ARGUS_BASE_URL.rstrip("/")
        self.headers = {}
        if settings.ARGUS_API_KEY:
            self.headers["X-API-Key"] = settings.ARGUS_API_KEY

    async def fetch_raw(self, request: FetchRawRequest) -> FetchRawResponse:
        url = f"{self.base_url}/api/fetch-raw"
        async with httpx.AsyncClient(timeout=float(request.timeout_seconds + 5)) as client:
            try:
                resp = await client.post(url, json=request.model_dump(), headers=self.headers)
                response_payload = FetchRawResponse(**resp.json())
                if response_payload.status == "error":
                    return response_payload
                if resp.status_code != 200:
                    return FetchRawResponse(status="error", http_status=resp.status_code)
                return response_payload
            except Exception as e:
                logger.error(f"Argus transport exception: {e}")
                return FetchRawResponse(status="error")
