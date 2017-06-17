import fnmatch
import subprocess
import logging
import threading
import os.path
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import parser
from . import symbols
from . import disasm

class BuildError(Exception):
    def __init__(self, message):
        self.message = message


class Watcher(FileSystemEventHandler):
    def __init__(self, directory, host='localhost', port=5000):
        # TODO: Check if directory is a pokeruby install
        # TODO: Check that the directory contains the necessary files

        self._logger = logging.getLogger('pokerubydiff')
        self._logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        self._logger.addHandler(ch)

        self._host = host
        self._port = port
        self._directory = directory
        self._changed_function = None
        self._update_file_cache()
        self._update_symbol_cache()

        paths = [
            os.path.join(directory, 'src'),
            os.path.join(directory, 'asm'),
            os.path.join(directory, 'include'),
        ]

        self._observer = Observer(timeout=0.1)

        for p in paths:
            self._observer.schedule(self, p, recursive=True)

        here = os.path.abspath(os.path.dirname(__file__))
        self._app = app = Flask(__name__, template_folder='public')
        self._socketio = SocketIO(app)

        @app.route('/')
        def hello():
            return render_template('index.html')

        @app.route("/assets/<path:filename>")
        def send_asset(filename):
            return send_from_directory(os.path.join(here, "public"), filename)

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
        self._socketio.run(self._app, host=self._host, port=self._port)
        self._observer.stop()
        self._observer.join()

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

        # 1. Trigger a rebuild
        self._socketio.emit('building')
        try:
            self._make()
        except BuildError as e:
            self._socketio.emit('build_error', e.message)
            return

        # 2. Find change location or load it from the cached location
        changed_function = None
        if self._matches(path, ('*.c',)):
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

        # 3. Get symbol address
        symbol = self._symbolcache.lookup_name(changed_function)
        if symbol == None:
            self._logger.info('Could not find address for function {}'.format(changed_function))
            return
        address = symbol.value & 0xFFFFFFFE # Ignore THUMB bit

        # 5. Disassemble
        with open(os.path.join(self._directory, 'pokeruby.elf'), 'rb') as f:
            modified_symbols = symbols.Symbols(f)

        with open(os.path.join(self._directory, 'pokeruby.gba'), 'rb') as f:
            modified_binary = f.read()

        original = disasm.Disassembler(self._original_binary).disassemble(address, self._symbolcache)
        modified = disasm.Disassembler(modified_binary).disassemble(address, modified_symbols)

        print(original)

        # 6. Diff
        # 8. Emit change
