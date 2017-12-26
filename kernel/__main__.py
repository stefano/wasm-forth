import shutil
import sys
import os

import assembler


BASE_PATH = os.path.abspath(os.path.dirname(__file__))

assembler.build_kernel(os.path.join(BASE_PATH, '../dist/kernel.wasm'))
shutil.copy(
    os.path.join(BASE_PATH, 'forth/core.f'),
    os.path.join(BASE_PATH, '../dist/core.f'),
)

if len(sys.argv) > 1 and sys.argv[1] == '--demo-repl':
    import http.server
    import socketserver

    shutil.copy(
        os.path.join(BASE_PATH, 'forth/core.f'),
        os.path.join(BASE_PATH, '../repl/dist/core.f'),
    )
    shutil.copy(
        os.path.join(BASE_PATH, '../dist/kernel.wasm'),
        os.path.join(BASE_PATH, '../repl/dist/kernel.wasm'),
    )

    os.chdir(os.path.join(BASE_PATH, '..', 'repl'))

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', 8080), http.server.SimpleHTTPRequestHandler) as httpd:
        print('Open your browser at http://localhost:8080/')
        httpd.serve_forever()
