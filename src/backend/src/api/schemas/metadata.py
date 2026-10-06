"""The common response envelope for native metadata-provider searches."""

from pydantic import BaseModel


class MetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    provider_errors: list[str] = []
    results: list[dict]
