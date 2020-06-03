from uuid import uuid1
from typing import Dict, List, Tuple


class MainModel:
    def __init__(self):
        self.requests: Dict[str, RequestModel] = {}


class RequestModel:
    def __init__(self,
                 url: str = '',
                 method: str = 'GET',
                 name: str = '',
                 request_body: str = '',
                 params: List[Tuple[str, str, str]] = None,
                 request_headers: List[Tuple[str, str, str]] = None,
                 # response_headers: List[Tuple[str, str, str]] = None,
                 saved: bool = False,
                 ):
        self.pk = str(uuid1())
        self.url = url
        self.method = method
        self.name = name
        self.params = params or [('', '', '')]
        self.request_body = request_body
        self.request_headers = request_headers or [('', '', '')]
        self.saved = saved
