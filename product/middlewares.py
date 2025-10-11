from fake_headers import Headers

class FakeHeaders:
    def __init__(self):
        self.headers = Headers()

    def process_request(self, request, spider):
        generator = self.headers.generate()
        for k,v in generator.items():
            request.headers[k] = v

