from flask import Flask, request, Response
from werkzeug.routing import Rule

app = Flask(__name__)
app.url_map.add(Rule('/', endpoint='index'))


@app.endpoint('index')
def echo():
    code = int(request.headers.get('x-response-code', 200))
    return Response(response=request.data,
                    status=code,
                    headers=dict(request.headers.items()),
                    mimetype=request.mimetype,
                    content_type=request.content_type,
                    direct_passthrough=True)
