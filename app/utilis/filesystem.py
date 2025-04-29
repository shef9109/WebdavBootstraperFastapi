from typing import Dict, Optional, List

class Resource:
    def __init__(self, content: bytes = b"", is_collection: bool = False):
        self.content = content
        self.is_collection = is_collection
        self.properties = {
            "getcontenttype": "application/octet-stream" if not is_collection else "httpd/unix-directory",
            "getcontentlength": len(content) if not is_collection else 0
        }
        self.locks: Dict[str, dict] = {}  # {token: lock_info}

class FileSystem:
    def __init__(self):
        self.resources: Dict[str, Resource] = {"/": Resource(is_collection=True)}

    def get_resource(self, path: str) -> Optional[Resource]:
        return self.resources.get(path)

    def create_resource(self, path: str, content: bytes = b"", is_collection: bool = False):
        self.resources[path] = Resource(content, is_collection)

    def delete_resource(self, path: str):
        if path in self.resources:
            del self.resources[path]

    def list_collection(self, path: str) -> List[str]:
        if path not in self.resources or not self.resources[path].is_collection:
            return []
        return [p for p in self.resources if p.startswith(path) and p != path]