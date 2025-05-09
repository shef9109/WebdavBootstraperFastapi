import hashlib
import mimetypes
import os
from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO
from typing import Optional

from app.schemas.schemas import FileInfo
from app.schemas.webdav import Collection, Prop, PropStat, Response, Multistatus
from app.utilis.formatters import unixdate2iso8601, unixdate2httpdate


class EMEMBER(Enum):
    MEMBER = 1
    COLLECTION = 2


ROOTFOLDER = "storage/"


class FileSystemMember(ABC):
    name: str  # filename
    fsname: str  # real filepath
    vname: str  # virtual filepath
    parent: Optional["FileSystemMember"]
    type: EMEMBER

    _properites: FileInfo | None = None
    _children: list["FileSystemMember"] | None = None

    @abstractmethod
    def send_data(self, stream: BytesIO | None, chunk_size: int, start: int, size: int):
        ...

    @abstractmethod
    def add_child(self, member: "FileSystemMember"):
        ...

    @property
    def properties(self) -> FileInfo:
        if self._properites is not None:
            return self._properites

        st = os.stat(self.fsname)
        m = hashlib.md5()
        m.update(self.fsname.encode('utf-8'))

        self._properites = FileInfo(
            creationdate=unixdate2iso8601(st.st_ctime),
            getlastmodified=unixdate2httpdate(st.st_mtime),
            displayname=self.name,
            getetag=m.hexdigest(),
            getcontentlength=st.st_size,  # if self.type == EMEMBER.MEMBER else None,
            getcontenttype=mimetypes.guess_type(self.name)[
                0] if self.type == EMEMBER.MEMBER else 'httpd/unix-directory',
            resourcetype='<D:collection/>' if self.type == EMEMBER.COLLECTION else None,
            ishidden=1 if self.name[0] == "." else None,
            isreadonly=1 if not os.access(self.fsname, os.W_OK) else None,
            isroot=1 if self.parent == '/home/' else None,
            iscollection=1 if self.type == EMEMBER.COLLECTION else None,
        )

        return self._properites

    def props(self, base_href: str = ''):
        return Response(
            href=self.name.replace(base_href, ""),
            propstat=PropStat(
                status='HTTP/1.1 200 OK',
                prop=Prop(
                    content_type=self.properties.getcontenttype if self.properties.getcontenttype else 'httpd/unix-directory',
                    content_length=self.properties.getcontentlength,
                    creation_date=self.properties.creationdate,
                    display_name=self.properties.displayname,
                    source=None,
                    last_modified=self.properties.getlastmodified,
                    content_language=self.properties.getcontentlanguage,
                    resource_type=Collection(actual=True) if self.type == EMEMBER.COLLECTION else None,
                    is_collection=1 if self.type == EMEMBER.COLLECTION else None,
                    e_tag=self.properties.getetag,
                )
            )
        )

    @abstractmethod
    def propfind(self): ...

    def __str__(self):
        return "{}: {} -> {}".format(self.type, self.vname, self.fsname)

    def __repr__(self):
        return f"FSMember(TYPE={self.type}, name={self.name} (path={self.vname}): resourse@{self.fsname}  # parent={self.parent})"


class File(FileSystemMember):

    def __init__(self, name, parent: FileSystemMember, fsname: str = None):
        self.parent = parent
        self.name = name
        self.fsname = ROOTFOLDER + (name if fsname is None else fsname)  # e.g. '/var/www/mysite/some.txt'
        self.vname = parent.vname + name  # e.g. '/mysite/some.txt'
        self.type = EMEMBER.MEMBER

    def send_data(self, stream: BytesIO | None, chunk_size: int, start: int, size: int):
        bytes_read = 0

        if stream is None:
            stream = open(self.fsname, mode='rb')

        stream.seek(start)

        while bytes_read < size:
            bytes_to_read = min(chunk_size,
                                size - bytes_read)
            yield stream.read(bytes_to_read)
            bytes_read = bytes_read + bytes_to_read

        stream.close()

    def propfind(self):
        return Multistatus(
            response=[self.props(base_href=os.path.split(self.vname)[0])]
        )

    def add_child(self, member: "FileSystemMember"):
        return None


class DirCollection(FileSystemMember):
    COLLECTION_MIME_TYPE = 'httpd/unix-directory'

    def __init__(self, name, parent: FileSystemMember = None, fsname: str = None):
        self.parent = parent
        self.name = name
        self.type = EMEMBER.COLLECTION

        if parent is not None:
            self.fsname = ROOTFOLDER + (name if fsname is None else fsname)  # e.g. '/var/www/mysite/some.txt'
            self.vname = parent.vname + name  # e.g. '/mysite/some.txt'
        else:
            self.fsname = ROOTFOLDER + (name if fsname is None else fsname)
            self.vname = name

        if self.fsname[-1] != os.sep:
            if self.fsname[-1] == '/':
                self.fsname = self.fsname[:-1] + os.sep
            else:
                self.fsname += os.sep

        if self.vname[-1] != '/':
            self.vname += '/'

    def add_child(self, member: "FileSystemMember"):
        if self._children is None:
            self._children = []

        self._children.append(member)
        if member.parent is None:
            member.parent = self

    def get_members(self):
        return self._children

    def send_data(self, stream: BytesIO | None, chunk_size: int, start: int, size: int):

        memb = self.get_members()
        data = '<html><head><title>{}</title></head><body>'.format(self.vname)
        data += '<table><tr><th>Name</th><th>Size</th><th>Timestamp</th></tr>'
        for m in memb:
            p = m.properties.model_dump()
            if 'getcontentlength' in p:
                p['size'] = int(p['getcontentlength'])
                p['timestamp'] = p['getlastmodified']
            else:
                p['size'] = 0
                p['timestamp'] = '-DIR-'
            data += '<tr><td>%s</td><td>%d</td><td>%s</td></tr>' % (p['displayname'], p['size'], p['timestamp'])
        data += '</table></body></html>'

        stream = BytesIO(data.encode('utf-8'))
        bytes_read = 0

        stream.seek(start)

        while bytes_read < size:
            bytes_to_read = min(chunk_size,
                                size - bytes_read)
            yield stream.read(bytes_to_read)
            bytes_read = bytes_read + bytes_to_read

        stream.close()

    def props(self, base_href: str = ''):
        res = super().props(base_href=base_href)
        quota_info = os.statvfs(ROOTFOLDER)

        res.propstat.prop.quota_used_bytes = (quota_info.f_blocks - quota_info.f_bavail) * quota_info.f_frsize
        res.propstat.prop.quota_available_bytes = quota_info.f_bavail * quota_info.f_frsize
        res.propstat.prop.quotaused = res.propstat.prop.quota_used_bytes
        res.propstat.prop.quota = res.propstat.prop.quota_available_bytes

        return res


    def propfind(self):
        return Multistatus(
            response=
            # [self.props(self.vname)] +
            [
                file.props(self.vname)
                for file in self.get_members()
            ]
        )


ROOT = DirCollection(name='/', fsname='storage')


def create_path(vpath: str, fname: str):
    vpath, name = os.path.split(vpath)
    elem = ROOT
    folders = vpath.split('/')
    for folder in folders:
        elem = DirCollection(folder, elem, fsname='')  # , fsname=ROOT.fsname)
    if name:
        elem = File(name, elem, fsname=fname)
    return elem



