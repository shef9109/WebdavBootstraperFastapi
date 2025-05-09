import os
from typing import Type

from sqlalchemy.orm import Session
from app.models.models import FileSystem
from app.models.webdav import create_path, File, DirCollection


def get_file(db: Session, file_path: str, user_id: int):
    if not file_path.startswith('/'):
        file_path = '/' + file_path
    if file_path.endswith('/'):
        file_path = file_path[:-1]
    res = (db.query(FileSystem).
           filter(FileSystem.vpath == file_path).
           filter(FileSystem.owner_id == user_id)).first()

    if not res:
        raise Exception("Not found " + file_path)

    if res.member_type == 2 and not file_path.endswith('/'):
        file_path += '/'

    file = create_path(file_path, fname=str(res.fname))

    if res.member_type == 2:
        nested_files: list[Type[FileSystem]] = (db.query(FileSystem).
                  filter(FileSystem.parent == res.fname).
                  filter(FileSystem.owner_id == user_id)
                                                # .filter(FileSystem.member_type == 1)
                                                ).all()


        for nested_file in nested_files:
            name = os.path.split(str(nested_file.vpath))[1]

            if nested_file.member_type == 2:
                file.add_child(
                    DirCollection(name, parent=file, fsname='')
                )
            else:
                file.add_child(
                    File(name, parent=file, fsname=str(nested_file.fname))
                )



    return file
