"""Pinned, local embedding models and the llama.cpp backend."""
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

DEFAULT = "light"
RUNTIME_BUILD = "b12359"
INSTRUCTION = "Retrieve mathematical statements, definitions, or proof techniques relevant to the query."
LIMIT = 512
PROFILES = {
    "mac8": {
        "model": "Qwen3-Embedding-4B", "quant": "Q4_K_M", "dimensions": 2560,
        "revision": "f4602530db1d980e16da9d7d3a70294cf5c190be",
        "sha256": "2b0cf8f17b4c723c27303015383c27ec4bf2d8314bb677d05e920dd70bb0f16b",
    },
    "light": {
        "model": "Qwen3-Embedding-0.6B", "quant": "Q8_0", "dimensions": 1024,
        "revision": "370f27d7550e0def9b39c1f16d3fbaa13aa67728",
        "sha256": "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439",
    },
    "gemma": {
        "model": "embeddinggemma-2", "owner": "ggml-org", "quant": "BF16", "dimensions": 768,
        "pooling": "mean", "query_prefix": "task: search result | query: ",
        "document_prefix": "title: none | text: ",
        "revision": "6ea3e3a309d12a4779cfda98b8c19800d2d5da71",
        "sha256": "68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216",
    },
    "mac16": {
        "model": "Qwen3-Embedding-8B", "quant": "Q5_K_M", "dimensions": 4096,
        "revision": "69d0e58a13e463cd99a9b83e3f5fee7c10265fab",
        "sha256": "022d33b4e2d97ef09a74feb13ef368cb7ca3a610ea2fb3e107199fa72c226e78",
    },
    "mac24": {
        "model": "Qwen3-Embedding-8B", "quant": "Q8_0", "dimensions": 4096,
        "revision": "69d0e58a13e463cd99a9b83e3f5fee7c10265fab",
        "sha256": "d20ddc71e8a5c4344f2343481e242233a997dc5eaff442427a945836c97b4deb",
    },
    "mac32": {
        "model": "Qwen3-Embedding-8B", "quant": "f16", "dimensions": 4096,
        "revision": "69d0e58a13e463cd99a9b83e3f5fee7c10265fab",
        "sha256": "9a2dfcc2e867828909456dd52a69e3775b677bdce1816f7cc55f3657393e7e53",
    },
}


def model_path(root, name):
    model = PROFILES[name]
    return root / "build/semantex/models" / f"{model['model']}-{model['quant']}.gguf"


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_setup(root, name):
    model = PROFILES[name]
    path = model_path(root, name)
    if path.is_file() and file_hash(path) == model["sha256"]:
        return path
    from urllib.request import urlopen

    path.parent.mkdir(parents=True, exist_ok=True)
    owner = model.get("owner", "Qwen")
    url = f"https://huggingface.co/{owner}/{model['model']}-GGUF/resolve/{model['revision']}/{path.name}"
    print(f"Downloading {path.name} from {owner} on Hugging Face.", file=sys.stderr)
    temporary = None
    try:
        with urlopen(url, timeout=30) as response, tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
            temporary = out.name
            digest = hashlib.sha256()
            for block in iter(lambda: response.read(1024 * 1024), b""):
                out.write(block)
                digest.update(block)
        if digest.hexdigest() != model["sha256"]:
            raise ValueError(f"unexpected SHA-256 for {path.name}")
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return path


class EmbeddingServer:
    def __init__(self, root, name):
        self.path = model_path(root, name)
        self.name = name
        self.model = PROFILES[name]
        self.active = False
        bundled = root / f"build/semantex/runtime/llama-{RUNTIME_BUILD}/llama-server"
        default_executable = str(bundled) if bundled.is_file() else "llama-server"
        executable = os.environ.get("SEMANTEX_LLAMA_SERVER", default_executable)
        self.executable = shutil.which(executable)
        if not self.executable:
            raise ValueError("install llama.cpp with llama-server or set SEMANTEX_LLAMA_SERVER")
        version = subprocess.run([self.executable, "--version"], capture_output=True, text=True, timeout=15)
        if version.returncode:
            raise ValueError("could not determine the llama-server version")
        self.version = (version.stdout + version.stderr).strip()
        self.gpu_layers = os.environ.get("SEMANTEX_GPU_LAYERS", "auto")
        if self.gpu_layers != "auto" and not self.gpu_layers.isdecimal():
            raise ValueError("SEMANTEX_GPU_LAYERS must be auto or a nonnegative integer")
        # The runtime reserves a context position beyond the 512-token input budget.
        self.arguments = ["--embeddings", "--pooling", self.model.get("pooling", "last"), "--parallel", "1",
                          "--ctx-size", str(LIMIT + 1), "--batch-size", str(LIMIT), "--ubatch-size", str(LIMIT),
                          "--n-gpu-layers", self.gpu_layers]

    @property
    def signature(self):
        return dict(version=1, model=self.model, runtime=self.version,
                    options=self.arguments, query_instruction=INSTRUCTION)

    def request(self, route, data=None):
        from http.client import HTTPConnection

        connection = HTTPConnection("127.0.0.1", self.port, timeout=120)
        try:
            headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
            connection.request("GET" if data is None else "POST", route,
                               body=None if data is None else json.dumps(data), headers=headers)
            response = connection.getresponse()
            body = json.loads(response.read())
            if response.status != 200:
                raise ValueError(f"llama-server {route}: HTTP {response.status}: {body.get('error', body)}")
            return body
        finally:
            connection.close()

    @contextmanager
    def running(self):
        if self.active:
            yield self
            return
        if not self.path.is_file():
            raise ValueError(f"run scripts/semantex rag setup --profile {self.name}")
        if file_hash(self.path) != self.model["sha256"]:
            raise ValueError(f"invalid weights for {self.name}; run rag setup")
        import socket
        from uuid import uuid4

        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.port = reservation.getsockname()[1]
        self.key = uuid4().hex
        command = [self.executable, "--model", str(self.path), "--host", "127.0.0.1",
                   "--port", str(self.port), "--api-key", self.key, "--log-verbosity", "3", *self.arguments]
        with tempfile.TemporaryFile() as log, subprocess.Popen(command, stdout=log, stderr=log) as process:
            try:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        if self.request("/health").get("status") == "ok":
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(0.05)
                else:
                    log.seek(0, os.SEEK_END)
                    log.seek(max(0, log.tell() - 3000))
                    raise ValueError("llama-server did not become ready:\n" + log.read().decode(errors="replace"))
                self.active = True
                self.pid = process.pid
                startup_log = os.pread(log.fileno(), 65536, 0).decode(errors="replace")
                self.offload = next((line.strip() for line in reversed(startup_log.splitlines())
                                     if "offloaded" in line and "layers to GPU" in line), None)
                yield self
            finally:
                self.active = False
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

    def vector(self, text, query=False):
        prefix = self.model.get("query_prefix", f"Instruct: {INSTRUCTION}\nQuery: ") if query else self.model.get("document_prefix", "")
        text = prefix + text
        tokens = self.request("/tokenize", {"content": text, "add_special": True, "parse_special": False})["tokens"]
        result = self.request("/v1/embeddings", {"input": tokens[:LIMIT]})
        return result["data"][0]["embedding"]


class ResidentModel:
    """Keep one llama.cpp session alive for the worker across embeddings."""
    def __init__(self, key, backend):
        self.key = key
        self.backend = backend
        self.session = None
        self.query_vector = lru_cache(maxsize=64)(lambda text: backend.vector(text, query=True))

    @property
    def signature(self):
        return self.backend.signature

    @contextmanager
    def running(self):
        from http.client import HTTPException

        if self.session is None:
            session = self.backend.running()
            session.__enter__()
            self.session = session
        try:
            yield self
        except (OSError, HTTPException):
            self.close()
            raise

    def vector(self, text, query=False):
        return self.query_vector(text) if query else self.backend.vector(text)

    def close(self):
        if self.session is not None:
            self.session.__exit__(None, None, None)
            self.session = None
