import shutil
import sys
import os

import assembler


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
DIST_PATH = os.path.join(BASE_PATH, '../dist')

if not os.path.exists(DIST_PATH):
    os.makedirs(DIST_PATH)

assembler.build_kernel(os.path.join(DIST_PATH, 'kernel.wasm'))
for file_name in ('core.f', 'vdom.f'):
    shutil.copy(
        os.path.join(BASE_PATH, os.path.join('forth', file_name)),
        os.path.join(DIST_PATH, file_name),
    )

if len(sys.argv) > 1 and sys.argv[1] == '--demo-repl':
    import http.server
    import socketserver

    REPL_DIST_PATH = os.path.join(BASE_PATH, '../repl/dist/')

    if not os.path.exists(REPL_DIST_PATH):
        os.makedirs(REPL_DIST_PATH)

    for file_name in ('core.f', 'vdom.f'):
        shutil.copy(
            os.path.join(BASE_PATH, 'forth', file_name),
            os.path.join(REPL_DIST_PATH, file_name),
        )
    shutil.copy(
        os.path.join(DIST_PATH, 'kernel.wasm'),
        os.path.join(REPL_DIST_PATH, 'kernel.wasm'),
    )

    os.chdir(os.path.join(BASE_PATH, '..', 'repl'))

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', 8080), http.server.SimpleHTTPRequestHandler) as httpd:
        print('Open your browser at http://localhost:8080/')
        httpd.serve_forever()
