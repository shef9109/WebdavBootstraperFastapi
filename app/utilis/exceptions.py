
class CustomNamedException(Exception):
    text: str

    def __init__(self, arg):
        super().__init__(self.text + arg)

class FileNotFoundException(CustomNamedException):
    text: str = "File not found"

class ResourceIsNotCollection(CustomNamedException):
    text: str = "File is not folder"

class AlreadyExistsException(CustomNamedException):
    text: str = "Already exists"