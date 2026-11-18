"""Exercise the pinned server's strict context boundary without model downloads."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantex_embeddings import EmbeddingServer, LIMIT


class EmbeddingBoundaryTests(unittest.TestCase):
    def test_full_input_budget_fits_the_runtime_context(self):
        # b12359 rejects prompts whose token count equals the context capacity.
        # The real-server counterpart is recorded in migration/rag-context-boundary.json.
        with patch('semantex_embeddings.shutil.which', return_value='/fixture/llama-server'), patch(
                'semantex_embeddings.subprocess.run', return_value=SimpleNamespace(
                    returncode=0, stdout='fixture b12359', stderr='')):
            backend = EmbeddingServer(Path('/fixture'), 'light')
        context = int(backend.arguments[backend.arguments.index('--ctx-size') + 1])
        for token_count in (LIMIT - 1, LIMIT, LIMIT + 100):
            with self.subTest(token_count=token_count):
                supplied = list(range(token_count))
                received = []
                def runtime(route, data):
                    if route == '/tokenize':
                        return {'tokens': supplied}
                    self.assertEqual(route, '/v1/embeddings')
                    received.extend(data['input'])
                    if len(received) >= context:
                        raise ValueError('request exceeds available context size')
                    return {'data': [{'embedding': [1.0] + [0.0] * 1023}]}
                backend.request = runtime
                self.assertEqual(len(backend.vector('mathematical content')), 1024)
                self.assertEqual(received, supplied[:LIMIT])


if __name__ == '__main__':
    unittest.main()
