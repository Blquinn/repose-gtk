from http import server


class EchoHandler(server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        request_path = self.path
        print("\n----- Request Start ----->\n")
        print(request_path)

        print("<----- Request End -----\n")
        self.send_response(200)
        self.send_header('X-Foo-Bar', 'Foobar')
        self.end_headers()

    def do_POST(self):
        request_path = self.path

        print("\n----- Request Start ----->\n")
        print(request_path)

        content_length = self.headers.get('content-length')
        length = int(content_length[0]) if content_length else 0

        print(self.headers)
        request_body = self.rfile.read(length)
        print(request_body)
        print("<----- Request End -----\n")

        response_code = int(self.headers.get('x-response-code', 200))
        self.send_response(response_code)
        if content_length:
            self.send_header('Content-Length', content_length)
        self.end_headers()
        if content_length:
            self.wfile.write(request_body)

    do_PUT = do_POST
    do_PATCH = do_POST
    do_GET = do_POST
    do_DELETE = do_POST


if __name__ == '__main__':
    srv = server.HTTPServer(('localhost', 4444), EchoHandler)
    srv.serve_forever()
