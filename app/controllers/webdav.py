from pathlib import Path

from fastapi import Request, status, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.repositories.files import get_file, create_folder, delete_file
from app.schemas.schemas import UserAuth
from app.utilis.exceptions import FileNotFoundException, ResourceIsNotCollection, AlreadyExistsException
from app.utilis.formatters import parse_int, builddict
from app.utilis.response import XMLResponse
from app.models.webdav import ROOT, EMEMBER
from app.schemas.webdav import Prop, PropStat, Response as WebdavResponse, Multistatus
from app.utilis.filesystem import FileSystem
from urllib.parse import unquote, urlparse
import os
import uuid
import logging
from app.repositories.auth import get_db, basic_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BYTES_PER_RESPONSE = 512

all_props = ['name', 'parentname', 'href', 'ishidden', 'isreadonly', 'getcontenttype',
             'contentclass', 'getcontentlanguage', 'creationdate', 'lastaccessed', 'getlastmodified',
             'getcontentlength', 'iscollection', 'isstructureddocument', 'defaultdocument',
             'displayname', 'isroot', 'resourcetype']
basic_props = ['name', 'getcontenttype', 'getcontentlength', 'creationdate', 'getlastmodified', 'iscollection']


async def get_body(request: Request):
    return await request.body()


class WebdavController:


    @staticmethod
    def OptionsIndexAction(request: Request, file_path: str = '', auth: UserAuth = Depends(basic_auth),
                       db: Session = Depends(get_db)):
        """
        @method options
        @path_params /{file_path:path}
        """
        return Response(
            status_code=200,
            content=None,
            headers={
                'Allow': 'GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY',
                'DAV': '1, 2',
                'Content-Length': '0',
                'X-Server-Copyright': 'WebDAV'
            }
        )


    @staticmethod
    def GetIndexAction(request: Request, file_path: str = '', auth: UserAuth = Depends(basic_auth),
                       db: Session = Depends(get_db)):
        """
        @method get
        @path_params /{file_path:path}
        """
        try:
            asked = request.headers.get("Range")

            file = get_file(db, file_path, auth.id)
            props = file.properties

            if asked is not None:
                bytes_requested = asked.split("=")[-1]
                start_byte_requested = parse_int(bytes_requested.split("-")[0])
                end_byte_requested = min(parse_int(bytes_requested.split("-")[1], BYTES_PER_RESPONSE),
                                         BYTES_PER_RESPONSE)
            else:
                start_byte_requested = 0
                end_byte_requested = BYTES_PER_RESPONSE


            end_byte_planned = min(start_byte_requested + end_byte_requested, props.getcontentlength)

            return StreamingResponse(
                file.send_data(
                    None,
                    chunk_size=BYTES_PER_RESPONSE,
                    start=start_byte_requested,
                    size=end_byte_planned - start_byte_requested  # props.get('getcontentlength')
                ),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes {start_byte_requested}-{end_byte_planned}/{props.getcontentlength}",
                    "Content-Type": props.getcontenttype,
                },
                status_code=206
            )

        except Exception as e:
            logger.error(e)
            return Response(status_code=404, content=None)
            # raise

    @staticmethod
    def HeadIndexAction(request: Request, file_path: str = '', auth: UserAuth = Depends(basic_auth),
                       db: Session = Depends(get_db)):
        """
        @method head
        @path_params /{file_path:path}
        """
        try:
            # asked = request.headers.get("Range")

            file = get_file(db, file_path, auth.id)
            props = file.properties
            #
            # if asked is not None:
            #     bytes_requested = asked.split("=")[-1]
            #     start_byte_requested = parse_int(bytes_requested.split("-")[0])
            #     end_byte_requested = min(parse_int(bytes_requested.split("-")[1], BYTES_PER_RESPONSE),
            #                              BYTES_PER_RESPONSE)
            # else:
            #     start_byte_requested = 0
            #     end_byte_requested = BYTES_PER_RESPONSE



            # end_byte_planned = min(start_byte_requested + end_byte_requested, props.getcontentlength)

            return Response(
                headers={
                    "Content-Length": str(props.getcontentlength),
                    "Content-Type": str(props.getcontenttype),
                },
                content=None,
                media_type='text/plain',
                status_code=200
            )

        except Exception as e:
            logger.error(e)
            return Response(status_code=404, content=None)
            # raise

    @staticmethod
    def PropfindIndexAction(request: Request, file_path: str = '', auth: UserAuth = Depends(basic_auth),
                            db: Session = Depends(get_db),
                            body: bytes = Depends(get_body)):
        """
        @method propfind
        @path_params /{file_path:path}
        """
        depth = 'infinity'
        if 'Depth' in request.headers:
            depth = request.headers['Depth'].lower()

        d = builddict(body.decode('utf-8')) # todo отдавать только требуемые поля, а не все

        try:
            file = get_file(db, file_path, auth.id)
        except Exception as e:
            return Response(
                status_code=status.HTTP_403_FORBIDDEN
            )

        if not file:
            if len(file_path) >= 1:
                return Response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    headers={
                        'Content-length': '0'
                    }
                )
            else:
                file = ROOT
        if depth != '0' and not file: #or file.type != EMEMBER.COLLECTION:
            return Response(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                headers={
                    'Content-length': '0'
                }
            )

        # print(
        #     file.propfind().to_xml()
        # )

        return Response(
            status_code=status.HTTP_207_MULTI_STATUS,
            content=file.propfind().to_xml()
        )


    @staticmethod
    def MkcolIndexAction(file_path: str = '', auth: UserAuth = Depends(basic_auth),
                         db: Session = Depends(get_db)):
        """
        @method mkcol
        @path_params /{file_path:path}
        """
        print(file_path)
        try:
            f = create_folder(db, file_path, auth.id)
            return Response(
                status_code=status.HTTP_201_CREATED,
                content=None
            )
        except FileNotFoundException:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content=None
            )
        except (ResourceIsNotCollection, AlreadyExistsException):
            return Response(
                status_code=status.HTTP_409_CONFLICT,
                content=None
            )

    @staticmethod
    def DeleteIndexAction(file_path: str = '', auth: UserAuth = Depends(basic_auth),
                          db: Session = Depends(get_db)):
        """
        @method delete
        @path_params /{file_path:path}
        """

        try:
            delete_file(db, file_path, auth.id)
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                content=None
            )
        except FileNotFoundException:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content=None
            )