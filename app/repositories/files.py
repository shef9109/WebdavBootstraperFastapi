import os
import time
from typing import Type

from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload
from app.models.models import FileSystem
from app.models.webdav import create_path, File, DirCollection, ROOTFOLDER
from app.utilis.exceptions import FileNotFoundException, ResourceIsNotCollection, AlreadyExistsException


def get_file(db: Session, file_path: str, user_id: int):
    if not file_path.startswith('/'):
        file_path = '/' + file_path
    if file_path.endswith('/'):
        file_path = file_path[:-1]
    res = (db.query(FileSystem).
           filter(FileSystem.vpath == file_path).
           filter(FileSystem.owner_id == user_id)).first()

    if not res:
        raise FileNotFoundException(file_path)

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


def create_folder(db: Session, folder_path: str, user_id: int):
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path
    if folder_path.endswith('/'):
        folder_path = folder_path[:-1]

    path, folder = os.path.split(folder_path)

    print(path, folder)

    res: Type[FileSystem]|None = (db.query(FileSystem).
           filter(FileSystem.vpath == path).
           filter(FileSystem.owner_id == user_id)).first()

    already_exists = (db.query(FileSystem).
                      filter(FileSystem.owner_id == user_id).
                      filter(FileSystem.vpath == folder_path)).first()

    print(f'{already_exists=}')

    if already_exists is not None:
        raise AlreadyExistsException(folder_path)

    if not res:
        raise FileNotFoundException(path)

    if res.member_type != 2:
        raise ResourceIsNotCollection(path)

    filename = str(time.time_ns())
    open(ROOTFOLDER + filename, 'a').close()

    f = FileSystem(
        fname=filename,
        vpath=folder_path,
        member_type=2,
        parent=str(res.fname),
        owner_id=user_id,
    )
    db.add(f)
    db.commit()
    db.refresh(f)

    return filename


def delete_file(db: Session, file_path: str, user_id: int):
    if not file_path.startswith('/'):
        file_path = '/' + file_path
    if file_path.endswith('/'):
        file_path = file_path[:-1]

    res: Type[FileSystem] | None = (db.query(FileSystem).options(joinedload(FileSystem.children)).
                                    filter(FileSystem.vpath == file_path).
                                    filter(FileSystem.owner_id == user_id)).first()

    if not res:
        raise FileNotFoundException(file_path)

    db.delete(res)
    db.commit()