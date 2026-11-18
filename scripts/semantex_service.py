"""Private per-checkout worker for interactive SemanTeX commands."""
from contextlib import redirect_stderr, redirect_stdout
import fcntl
import io
import json
import os
from pathlib import Path
import signal
import socket
from stat import S_ISSOCK
import subprocess
import sys


COMMANDS = {"get", "show", "locate", "deps", "rdeps", "ancestors", "descendants",
            "refs", "backrefs", "why", "order", "frontier", "fingerprint",
            "links", "search", "neighbors", "context"}
RAG_ACTIONS = {"build", "status", "stop"}
ENVIRONMENT = ("SEMANTEX_LLAMA_SERVER", "SEMANTEX_GPU_LAYERS", "PATH")


def can_serve(args):
    return bool(args) and (args[0] in COMMANDS or
                           (len(args) > 1 and args[0] == "rag" and args[1] in RAG_ACTIONS))


def code_version():
    return [[path.name, path.stat().st_mtime_ns, path.stat().st_size]
            for path in sorted(Path(__file__).parent.glob("*.py")) if path.name.startswith(("semantex", "manuscript_graph"))]


def connect(path):
    connection = socket.socket(socket.AF_UNIX)
    try:
        connection.connect(str(path))
        return connection
    except (FileNotFoundError, ConnectionRefusedError):
        connection.close()
        return None
    except OSError:
        connection.close()
        raise


def private_socket(root, start):
    directory = root / "build/semantex/service"
    if start:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    elif not directory.exists():
        return None
    info = directory.lstat()
    if directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        return None
    path = directory / "query.sock"
    if len(os.fsencode(path)) >= 104:
        return None
    with (directory / "start.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        connection = connect(path)
        if connection is not None or not start:
            return connection
        if path.exists():
            if not S_ISSOCK(path.lstat().st_mode):
                return None
            path.unlink()
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path))
            listener.listen(16)
            try:
                subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(root), str(listener.fileno())],
                                 pass_fds=(listener.fileno(),), start_new_session=True,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                path.unlink()
                raise
        return connect(path)


def query(root, args):
    if not can_serve(args):
        return None
    stop = args == ["rag", "stop"]
    if os.environ.get("SEMANTEX_ONESHOT") and not stop:
        return None
    request = {"args": args, "version": code_version(), "env": {key: os.environ.get(key) for key in ENVIRONMENT}}
    for attempt in range(2):
        try:
            connection = private_socket(root, start=not stop)
        except OSError:
            return None
        if connection is None:
            return None
        with connection, connection.makefile("rb") as reader:
            connection.sendall(json.dumps(request).encode() + b"\n")
            line = reader.readline()
        if not line:
            raise ValueError("the SemanTeX worker exited before completing the command")
        response = json.loads(line)
        if response.get("restart") and attempt == 0:
            continue
        sys.stdout.write(response.get("stdout", ""))
        sys.stderr.write(response.get("stderr", ""))
        return response.get("status", 1)
    return None


class Worker:
    def __init__(self, root):
        self.root = root
        self.current_graph = None
        self.snapshot_stamp = None
        self.current_model = None
        self.current_index = None
        self.lexical_text = {}

    def graph(self, graph_type, root):
        from semantex_cache import load_graph, signature, stamp

        def graph_stamp():
            try:
                return stamp(root / "build/semantex/graph.sqlite3")
            except FileNotFoundError:
                return None

        inputs = signature(root)
        previous = self.current_graph if self.snapshot_stamp == graph_stamp() else None
        if inputs is not None and previous is not None and previous.cache_signature == inputs.full:
            # Review support includes live files outside the graph's source set.
            self.current_graph.reset_review_cache()
            return self.current_graph
        graph = load_graph(graph_type, root, inputs=inputs, save_snapshot=self.current_graph is None,
                           previous=previous)
        self.snapshot_stamp = graph_stamp()
        if graph is not previous:
            if self.current_index is not None:
                self.current_index[1].clear_inputs()
            self.lexical_text.clear()
        self.current_graph = graph if not graph.errors and getattr(graph, "cache_signature", None) else None
        return graph

    def embedder(self, profile):
        from semantex_cache import stamp
        from semantex_embeddings import EmbeddingServer, ResidentModel, model_path

        path = model_path(self.root, profile)
        key = profile, stamp(path) if path.is_file() else None, tuple(os.environ.get(name) for name in ENVIRONMENT)
        model = self.current_model
        executable = Path(model.backend.executable) if model is not None else None
        if model is None or model.key != key or not executable.is_file() or stamp(executable) != model.tool_stamp:
            self.close_model()
            backend = EmbeddingServer(self.root, profile)
            self.current_model = ResidentModel(key, backend)
            self.current_model.tool_stamp = stamp(Path(backend.executable))
        return self.current_model

    def model_status(self):
        if self.current_model is None or self.current_model.session is None:
            return None
        backend = self.current_model.backend
        return {"profile": backend.name, "pid": backend.pid, "offload": backend.offload}

    def index(self, profile, dimensions):
        from semantex_rag import VectorIndex

        if self.current_index is None or self.current_index[0] != profile:
            self.current_index = profile, VectorIndex(self.root, profile, dimensions, resident=True)
        return self.current_index[1]

    def close_model(self):
        if self.current_model is not None:
            self.current_model.close()
            self.current_model = None


def serve(root, descriptor):
    import sqlite3
    from manuscript_graph import main

    def terminate(*_):
        raise SystemExit

    signal.signal(signal.SIGTERM, terminate)
    worker = Worker(root)
    version = code_version()
    with socket.socket(fileno=descriptor) as listener:
        path = Path(listener.getsockname())
        identity = path.lstat().st_ino
        try:
            while True:
                connection, _ = listener.accept()
                with connection, connection.makefile("rb") as reader:
                    connection.settimeout(5)
                    try:
                        request = json.loads(reader.readline(1024 * 1024))
                    except (OSError, ValueError):
                        continue
                    connection.settimeout(None)
                    args = request.get("args", [])
                    stop = args == ["rag", "stop"]
                    restart = request.get("version") != version and not stop
                    response = {"status": 0}
                    if restart or stop:
                        worker.close_model()
                        # Allow the next client to bind a new listener before replying.
                        path.unlink()
                        response.update(restart=True) if restart else response.update(stdout="Stopped SemanTeX worker.\n")
                    elif not can_serve(args):
                        response.update(status=2, stderr="Unsupported SemanTeX worker command.\n")
                    else:
                        for name in ENVIRONMENT:
                            value = request["env"][name]
                            if value is None:
                                os.environ.pop(name, None)
                            else:
                                os.environ[name] = value
                        output, errors = io.StringIO(), io.StringIO()
                        with redirect_stdout(output), redirect_stderr(errors):
                            try:
                                response["status"] = main(args, worker=worker)
                            except SystemExit as exc:
                                response["status"] = exc.code
                            except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
                                print(f"error: {exc}", file=sys.stderr)
                                response["status"] = 1
                        response.update(stdout=output.getvalue(), stderr=errors.getvalue())
                    try:
                        connection.sendall(json.dumps(response).encode() + b"\n")
                    except OSError:
                        pass
                    if stop or restart:
                        return
        finally:
            worker.close_model()
            if path.exists() and path.lstat().st_ino == identity:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    serve(Path(sys.argv[1]), int(sys.argv[2]))
