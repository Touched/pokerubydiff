import fnmatch
import subprocess
import logging
import threading
import os.path
import asyncio
import hashlib
from aiohttp import web
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from . import parser
from . import symbols
from . import disasm
from . import diff

HASH_NAME = 'sha1'

class BuildError(Exception):
    def __init__(self, message):
        self.message = message


class Server(FileSystemEventHandler):
    def __init__(self, directory, *, host='localhost', port=5000,
                 function=None, no_reload_symbols=False):
        # TODO: Check if directory is a pokeruby install
        # TODO: Check that the directory contains the necessary files

        self._logger = logging.getLogger('pokerubydiff')
        self._logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self._logger.addHandler(ch)

        self._host = host
        self._port = port
        self._diff = None
        self._directory = directory
        self._changed_function = function
        self._update_file_cache()
        self._update_symbol_cache()
        self._message_queue = asyncio.Queue()
        self._no_reload_symbols = no_reload_symbols

        paths = [
            os.path.join(directory, 'src'),
            os.path.join(directory, 'asm'),
            os.path.join(directory, 'include'),
        ]

        self._observer = Observer(timeout=0.1)

        for p in paths:
            self._observer.schedule(self, p, recursive=True)

        public_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'public')

        async def index(request):
            with open(os.path.join(public_dir, 'index.html')) as f:
                return web.Response(text=f.read(), content_type='text/html')

        async def socket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)

            request.app['websockets'].append(ws)

            # New connections should receive the 'diff' event
            if self._diff != None:
                await ws.send_json({
                    'type': 'diff',
                    'data': self._diff,
                })

            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        # TODO: Handle client response
                        print(msg)
            finally:
                request.app['websockets'].remove(ws)

            return ws

        async def broadcast_messages(app):
            while True:
                type, data = await self._message_queue.get()
                for ws in app['websockets']:
                    ws.send_json({
                        'type': type,
                        'data': data,
                    })


        async def start_background_tasks(app):
            app['message_broadcaster'] = app.loop.create_task(broadcast_messages(app))


        async def cleanup_background_tasks(app):
            app['message_broadcaster'].cancel()
            await app['message_broadcaster']


        self._app = web.Application()
        self._app['websockets'] = []
        self._app.on_startup.append(start_background_tasks)
        self._app.on_cleanup.append(cleanup_background_tasks)
        self._app.router.add_get('/', index)
        self._app.router.add_get('/socket', socket)
        self._app.router.add_static('/assets', public_dir)

        if self._changed_function != None:
            self._trigger_build()

    def on_created(self, event):
        if self._observer.__class__.__name__ == 'InotifyObserver':
            # inotify also generates modified events for created files
            return

        if not event.is_directory:
            self._on_change(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._on_change(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._on_change(event.dest_path)

    def run(self):
        self._logger.info('Starting server at http://{}:{}'.format(self._host, self._port))
        self._observer.start()
        web.run_app(self._app)
        self._observer.stop()
        self._observer.join()

    def _broadcast(self, event, message=None):
        self._message_queue.put_nowait((event, message))

    def _matches(self, filename, patterns):
        return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)

    def _update_file_cache(self):
        self._filecache = parser.cache_files(self._directory, '**/*.c')

    def _update_symbol_cache(self):
        """
        Update the cached symbols for the original pokeruby binary file
        """
        with open(os.path.join(self._directory, 'basepokeruby.elf'), 'rb') as f:
            self._symbolcache = symbols.Symbols(f)

        with open(os.path.join(self._directory, 'basepokeruby.gba'), 'rb') as f:
            self._original_binary = f.read()
            h = hashlib.new(HASH_NAME)
            h.update(self._original_binary)
            self._original_hash = h.digest()

    def _make(self):
        self._logger.info('Starting a new build')
        proc = subprocess.Popen(['make'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode()
            self._logger.info('Build error:\n' + error)
            raise BuildError(error)
        else:
            self._logger.info('Build success')

    def _on_change(self, path):
        if not self._matches(path, ('*.c', '*.s', '*.asm', '*.inc', '*.h')):
            return False

        self._trigger_build(path)

    def _trigger_build(self, path=None):
        # 1. Trigger a rebuild
        self._broadcast('building')
        try:
            self._make()
        except BuildError as e:
            self._broadcast('build_error', e.message)
            return

        # 2. Check for a match
        with open(os.path.join(self._directory, 'pokeruby.gba'), 'rb') as f:
            modified_binary = f.read()

        h = hashlib.new(HASH_NAME)
        h.update(modified_binary)

        if self._original_hash == h.digest():
            self._logger.info('Match')
            self._broadcast('match')

        # 3. Find change location or load it from the cached location
        changed_function = None
        if path and self._matches(path, ('*.c',)):
            changed_function = parser.find_changed_function_name(path, self._filecache)

            if changed_function != None:
                self._changed_function = changed_function
        if changed_function == None:
            if self._changed_function == None:
                # Could not find the location of change, give up
                self._logger.info('Could not find a changed function')
                return

            changed_function = self._changed_function
        self._update_file_cache()

        # 4. Get symbol address
        symbol = self._symbolcache.lookup_name(changed_function)
        if symbol == None:
            self._logger.info('Could not find address for function {}'.format(changed_function))
            return
        address = symbol.value & 0xFFFFFFFE # Ignore THUMB bit

        # 5. Disassemble
        if self._no_reload_symbols:
            modified_symbols = self._symbolcache
        else:
            with open(os.path.join(self._directory, 'pokeruby.elf'), 'rb') as f:
                modified_symbols = symbols.Symbols(f)

        original = disasm.Disassembler(self._original_binary).disassemble(
            address,
            self._symbolcache,
        )
        modified = disasm.Disassembler(modified_binary).disassemble(
            address,
            modified_symbols,
        )

        # 6. Diff
        differ = diff.DisasmDiff()
        self._diff = list(differ.diff(original, modified))

        # 7. Emit change
        self._broadcast('diff', self._diff)
