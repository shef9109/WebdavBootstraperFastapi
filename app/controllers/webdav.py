from pathlib import Path

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import Response
from app.utilis.response import XMLResponse
from app.models.webdav import Prop, PropStat, Response as WebdavResponse, Multistatus
from app.utilis.filesystem import FileSystem
from urllib.parse import unquote, urlparse
import os
import uuid
import logging

from app.resources.auth import basic_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_path(path: str) -> str:
    path = unquote(path)
    if not path.startswith("/"):
        path = "/" + path
    return os.path.normpath(path)

BASE_FILES_PATH = Path(__file__).parent.parent.parent / "files"

def get_user_path(user):
    user_path = os.path.join(BASE_FILES_PATH, user)
    os.makedirs(user_path, exist_ok=True)
    return user_path


class WebdavController:
    response_class = XMLResponse

    def OptionsIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method options
        @response_model XMLResponse
        """
        try:
            headers = {
                "DAV": "1, 2",
                "Allow": "OPTIONS, PROPFIND, PROPPATCH, MKCOL, GET, PUT, DELETE, COPY, MOVE, LOCK, UNLOCK",
                "MS-Author-Via": "DAV"
            }
            return Response(status_code=status.HTTP_200_OK, headers=headers)
        except Exception as e:
            logger.error(f"OPTIONS error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def PropfindIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method propfind
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

            depth = request.headers.get("Depth", "0").lower()
            responses = []
            prop = Prop(
                content_type=resource.properties.get("getcontenttype", ""),
                content_length=resource.properties.get("getcontentlength", 0)
            )
            propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
            responses.append(WebdavResponse(href=path, propstat=propstat))

            if depth != "0" and resource.is_collection:
                for child_path in self.fs.list_collection(path):
                    child = self.fs.get_resource(child_path)
                    prop = Prop(
                        content_type=child.properties.get("getcontenttype", ""),
                        content_length=child.properties.get("getcontentlength", 0)
                    )
                    propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
                    responses.append(WebdavResponse(href=child_path, propstat=propstat))

            multistatus = Multistatus(response=responses)
            return XMLResponse(content=multistatus, status_code=status.HTTP_207_MULTI_STATUS)
        except Exception as e:
            logger.error(f"PROPFIND error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def ProppatchIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method proppatch
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

            prop = Prop(
                content_type=resource.properties.get("getcontenttype", ""),
                content_length=resource.properties.get("getcontentlength", 0)
            )
            propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
            response = WebdavResponse(href=path, propstat=propstat)
            multistatus = Multistatus(response=response)
            return XMLResponse(content=multistatus, status_code=status.HTTP_207_MULTI_STATUS)
        except Exception as e:
            logger.error(f"PROPPATCH error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def MkcolIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method mkcol
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            if self.fs.get_resource(path):
                raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Resource already exists")
            self.fs.create_resource(path, is_collection=True)
            return Response(status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"MKCOL error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def GetIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method get
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource or resource.is_collection:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

            headers = {
                "Content-Type": resource.properties.get("getcontenttype", "application/octet-stream"),
                "Content-Length": str(resource.properties.get("getcontentlength", 0))
            }
            return Response(content=resource.content, headers=headers, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"GET error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @staticmethod
    async def PutIndexAction(request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method put
        @response_model Response
        """
        try:
            user_path = get_user_path(user.username)
            user_path = normalize_path(user_path)
            content = await request.body()
            with open(user_path + '/test.txt', "wb") as f:
                f.write(content)
            return Response(status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"PUT error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def DeleteIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method delete
        @@response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
            self.fs.delete_resource(path)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"DELETE error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def CopyIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method copy
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            destination_header = request.headers.get("Destination", "")
            destination = self.normalize_path(urlparse(unquote(destination_header)).path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
            self.fs.create_resource(destination, content=resource.content, is_collection=resource.is_collection)
            return Response(status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"COPY error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def MoveIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method move
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            destination_header = request.headers.get("Destination", "")
            destination = self.normalize_path(urlparse(unquote(destination_header)).path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
            self.fs.create_resource(destination, content=resource.content, is_collection=resource.is_collection)
            self.fs.delete_resource(path)
            return Response(status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"MOVE error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def LockIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method lock
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

            lock_token = f"opaquelocktoken:{uuid.uuid4()}"
            resource.locks[lock_token] = {"depth": "infinity", "timeout": "Infinite", "owner": ""}

            prop = Prop(
                content_type=resource.properties.get("getcontenttype", ""),
                content_length=resource.properties.get("getcontentlength", 0)
            )
            propstat = PropStat(status="HTTP/1.1 200 OK", prop=prop)
            response = WebdavResponse(href=path, propstat=propstat)
            multistatus = Multistatus(response=response)
            headers = {"Lock-Token": f"<{lock_token}>"}
            return XMLResponse(content=multistatus, status_code=status.HTTP_200_OK, headers=headers)
        except Exception as e:
            logger.error(f"LOCK error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def UnlockIndexAction(self, request: Request, path: str = "", user=Depends(basic_auth)) -> XMLResponse:
        """
        @method unlock
        @response_model XMLResponse
        """
        try:
            path = self.normalize_path(path)
            resource = self.fs.get_resource(path)
            if not resource:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

            lock_token = request.headers.get("Lock-Token", "").strip("<>")
            if lock_token not in resource.locks:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid lock token")
            del resource.locks[lock_token]
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"UNLOCK error for path {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def __str__(self):
        return f"{self.__class__.__name__} handles WebDAV requests"
