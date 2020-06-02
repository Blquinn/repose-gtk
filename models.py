class Request:
    def __init__(self, url: str = '', method: str = '', name: str = None):
        self.url = url
        self.method = method
        self.name = name
