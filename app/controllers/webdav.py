from fastapi import APIRouter, Depends, HTTPException, Response as Resp, Request
from pydantic_xml import BaseXmlModel
from app.utilis.response import XMLResponse
from app.models.webdav import (
    Prop, PropStat, Response, Multistatus
)

class WebdavController:
    response_model = XMLResponse
    
    @staticmethod
    def WebdavAction(response: Resp):
        """Webdav tools
        
        @response_model XMLResponse
        @method get
        """
        model = Multistatus(
            response=Response(
                href='https://webdavserver.ru/webdav/docs/myFile.txt',
                propstat=PropStat(
                    status='HTTP/1.1 200 OK',
                        prop=Prop(
                            content_type='text/plain',
                            content_length=33
                        )
                    )
                )
            )
        return XMLResponse(model)

        

