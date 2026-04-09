import sys, os

sys.path.insert(0, '/home/AtttendX/AttendX/backend')
sys.path.insert(0, '/home/AtttendX/AttendX')
os.chdir('/home/AtttendX/AttendX')
os.environ.setdefault('SECRET_KEY', 'attendx-production-secret-2024')

from main import app as fastapi_app

class ASGIMiddleware:
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    def __call__(self, environ, start_response):
        import asyncio
        async def run():
            scope = {
                'type': 'http', 'asgi': {'version': '3.0'},
                'http_version': '1.1', 'method': environ['REQUEST_METHOD'],
                'path': environ.get('PATH_INFO', '/'),
                'query_string': environ.get('QUERY_STRING', '').encode(),
                'root_path': environ.get('SCRIPT_NAME', ''),
                'scheme': environ.get('wsgi.url_scheme', 'https'),
                'server': (environ.get('SERVER_NAME'), int(environ.get('SERVER_PORT', 443))),
                'headers': [
                    (k[5:].lower().replace('_','-').encode(), v.encode())
                    for k,v in environ.items() if k.startswith('HTTP_')
                ] + [
                    (b'content-type', environ.get('CONTENT_TYPE','').encode()),
                    (b'content-length', environ.get('CONTENT_LENGTH','0').encode()),
                ],
            }
            body = environ['wsgi.input'].read(int(environ.get('CONTENT_LENGTH') or 0))
            started, chunks = [], []
            async def receive(): return {'type':'http.request','body':body,'more_body':False}
            async def send(msg):
                if msg['type']=='http.response.start': started.append((msg['status'],msg['headers']))
                elif msg['type']=='http.response.body': chunks.append(msg.get('body',b''))
            await self.asgi_app(scope, receive, send)
            return started, chunks
        started, chunks = asyncio.run(run())
        code, headers = started[0]
        codes = {200:'OK',201:'Created',204:'No Content',301:'Moved Permanently',
            400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',
            405:'Method Not Allowed',409:'Conflict',410:'Gone',422:'Unprocessable Entity',500:'Internal Server Error'}
        start_response(f'{code} {codes.get(code,"OK")}', [(k.decode(),v.decode()) for k,v in headers])
        return chunks

application = ASGIMiddleware(fastapi_app)
