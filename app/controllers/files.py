from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
from app.utilis.response import XMLResponse
from app.models.webdav import Prop, PropStat, Response as WebdavResponse, Multistatus
from app.utilis.filesystem import FileSystem
from urllib.parse import unquote
import os
import uuid

router = APIRouter(tags=["webdav"])

class WebdavController:
    def __init__(self):
        self.fs = FileSystem()
        self.router = router

    def normalize_path(self, path: str) -> str:
        path = unquote(path)
        if not path.startswith("/"):
            path = "/" + path
        return os.path.normpath(path)

    @router.options("/{path:path}", response_class=Response)
    async def options_action(self, request: Request, path: str = "") -> Response:
        """
        @method options
        """
        headers = {
            "DAV": "1, 2",
            "Allow": "OPTIONS, PROPFIND, PROPPATCH, MKCOL, GET, PUT, DELETE, COPY, MOVE, LOCK, UNLOCK",
            "MS-Author-Via": "DAV"
        }
        return Response(status_code=status.HTTP_200_OK, headers=headers)

    @router.api_route("/{path:path}", methods=["PROPFIND"], response_class=XMLResponse)
    async def propfind_action(self, request: Request, path: str = "") -> Multistatus:
        """
        @method propfind
        @response_model Multistatus
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        depth = request.headers.get("Depth", "0").lower()
        responses = []
        prop = Prop(
            content_type=resource.properties["getcontenttype"],
            content_length=resource.properties["getcontentlength"]
        )
        propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
        responses.append(WebdavResponse(href=path, propstat=propstat))

        if depth != "0" and resource.is_collection:
            for child_path in self.fs.list_collection(path):
                child = self.fs.get_resource(child_path)
                prop = Prop(
                    content_type=child.properties["getcontenttype"],
                    content_length=child.properties["getcontentlength"]
                )
                propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
                responses.append(WebdavResponse(href=child_path, propstat=propstat))

        multistatus = Multistatus(response=responses[0])
        return XMLResponse(content=multistatus, status_code=status.HTTP_207_MULTI_STATUS)

    @router.api_route("/{path:path}", methods=["PROPPATCH"], response_class=XMLResponse)
    async def proppatch_action(self, request: Request, path: str = "") -> Multistatus:
        """
        @method proppatch
        @response_model Multistatus
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        prop = Prop(
            content_type=resource.properties["getcontenttype"],
            content_length=resource.properties["getcontentlength"]
        )
        propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
        response = WebdavResponse(href=path, propstat=propstat)
        multistatus = Multistatus(response=response)
        return XMLResponse(content=multistatus, status_code=status.HTTP_207_MULTI_STATUS)

    @router.api_route("/{path:path}", methods=["MKCOL"], response_class=Response)
    async def mkcol_action(self, request: Request, path: str = "") -> Response:
        """
        @method mkcol
        """
        path = self.normalize_path(path)
        if self.fs.get_resource(path):
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
        self.fs.create_resource(path, is_collection=True)
        return Response(status_code=status.HTTP_201_CREATED)

    @router.get("/{path:path}", response_class=Response)
    async def get_action(self, request: Request, path: str = "") -> Response:
        """
        @method get
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource or resource.is_collection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        headers = {
            "Content-Type": resource.properties["getcontenttype"],
            "Content-Length": str(resource.properties["getcontentlength"])
        }
        return Response(content=resource.content, headers=headers, status_code=status.HTTP_200_OK)

    @router.put("/{path:path}", response_class=Response)
    async def put_action(self, request: Request, path: str = "") -> Response:
        """
        @method put
        """
        path = self.normalize_path(path)
        content = await request.body()
        self.fs.create_resource(path, content=content, is_collection=False)
        return Response(status_code=status.HTTP_201_CREATED)

    @router.delete("/{path:path}", response_class=Response)
    async def delete_action(self, request: Request, path: str = "") -> Response:
        """
        @method delete
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        self.fs.delete_resource(path)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.api_route("/{path:path}", methods=["COPY"], response_class=Response)
    async def copy_action(self, request: Request, path: str = "") -> Response:
        """
        @method copy
        """
        path = self.normalize_path(path)
        destination = self.normalize_path(
            request.headers.get("Destination", "").replace(request.url.scheme + "://" + request.url.netloc, "")
        )
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        self.fs.create_resource(destination, content=resource.content, is_collection=resource.is_collection)
        return Response(status_code=status.HTTP_201_CREATED)

    @router.api_route("/{path:path}", methods=["MOVE"], response_class=Response)
    async def move_action(self, request: Request, path: str = "") -> Response:
        """
        @method move
        """
        path = self.normalize_path(path)
        destination = self.normalize_path(
            request.headers.get("Destination", "").replace(request.url.scheme + "://" + request.url.netloc, "")
        )
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        self.fs.create_resource(destination, content=resource.content, is_collection=resource.is_collection)
        self.fs.delete_resource(path)
        return Response(status_code=status.HTTP_201_CREATED)

    @router.api_route("/{path:path}", methods=["LOCK"], response_class=XMLResponse)
    async def lock_action(self, request: Request, path: str = "") -> Multistatus:
        """
        @method lock
        @response_model Multistatus
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        lock_token = f"opaquelocktoken:{uuid.uuid4()}"
        resource.locks[lock_token] = {"depth": "infinity", "timeout": "Infinite", "owner": ""}

        prop = Prop(
            content_type=resource.properties["getcontenttype"],
            content_length=resource.properties["getcontentlength"]
        )
        propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
        response = WebdavResponse(href=path, propstat=propstat)
        multistatus = Multistatus(response=response)
        headers = {"Lock-Token": f"<{lock_token}>"}
        return XMLResponse(content=multistatus, status_code=status.HTTP_200_OK, headers=headers)

    @router.api_route("/{path:path}", methods=["UNLOCK"], response_class=Response)
    async def unlock_action(self, request: Request, path: str = "") -> Response:
        """
        @method unlock
        """
        path = self.normalize_path(path)
        resource = self.fs.get_resource(path)
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        lock_token = request.headers.get("Lock-Token", "").strip("<>")
        if lock_token not in resource.locks:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)
        del resource.locks[lock_token]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def __str__(self):
        return f"{self.__class__.__name__} serving WebDAV requests" 