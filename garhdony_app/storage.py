from django.core.files.storage import FileSystemStorage
import os

class DogmasFileSystemStorage(FileSystemStorage):
    """
    This solved some problem related to django being too shy about overwriting files.
    """
    def get_available_name(self, name, max_length=None):
        if os.path.exists(self.path(name)):
            os.remove(self.path(name))
        return name
