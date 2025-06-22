from typing import Union, List, Optional
from io import BytesIO

class PostAttachment:
    """
    Abstract base class for post attachments.
    This class defines the
    """

class Video:
    def __init__(self, path: str, alt_text: str = "") -> None: ...

class Image:
    def __init__(self, image: Union[str, BytesIO], alt_text: str = "") -> None: ...

class Post:
    def __init__(
        self,
        content: str,
        images: Optional[List[Image]] = None,
        video: Optional[Video] = None,
        with_attachments: Optional[Union[PostAttachment, List[PostAttachment]]] = None,
    ) -> None: ...

class WebCard(PostAttachment):
    def __init__(self, url: str) -> None: ...

class Client:
    def __init__(self) -> None: ...
    def authenticate(self, handle: str, app_password: str) -> None: ...
    def post(self, post: Post) -> None: ...
