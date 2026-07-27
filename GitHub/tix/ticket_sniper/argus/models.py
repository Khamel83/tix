from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class FetchRawRequest(BaseModel):
    url: str
    render: str = "none"
    cache: bool = False
    extractors: List[str] = Field(default_factory=lambda: ["local_only"])
    impersonate: str = "chrome"
    egress: str = "residential"
    timeout_seconds: int = 25
    headers: Dict[str, str] = Field(default_factory=dict)

class FetchRawResponse(BaseModel):
    status: str
    http_status: Optional[int] = None
    final_url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    body: str = ""
    body_sha256: Optional[str] = None
    render_mode_used: Optional[str] = None
    extractor_used: Optional[str] = None
    egress_used: Optional[str] = None
    elapsed_ms: int = 0
    from_cache: bool = False
