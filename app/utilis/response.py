import typing
from fastapi.responses import Response
from pydantic import BaseModel
from pydantic_xml import BaseXmlModel, create_model
from starlette.background import BackgroundTask


class XMLResponse(Response):
    media_type = "application/xml"

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
        if content is None:
            return b""
        if not isinstance(content, BaseXmlModel):
            raise NotImplementedError
        return content.to_xml(
            pretty_print=True,
            encoding='UTF-8',
            standalone=True 
        )
