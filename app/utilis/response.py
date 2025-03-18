import typing
from fastapi import Response
import pydantic_xml
from starlette.background import BackgroundTask

class XMLResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: typing.Any) -> bytes:
        return content.to_xml(
            pretty_print=True,
            encoding='UTF-8',
            standalone=True 
        )