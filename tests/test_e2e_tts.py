import io
import json
import os
import subprocess
import sys
import time
import unittest
import wave
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


@unittest.skipUnless(os.environ.get("TOUCAN_RUN_E2E") == "1", "set TOUCAN_RUN_E2E=1 to load the speech models")
class CherokeeSynthesisE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = int(os.environ.get("TOUCAN_TEST_PORT", "18765"))
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        environment = os.environ.copy()
        environment["TOUCAN_HOST"] = "127.0.0.1"
        environment["TOUCAN_PORT"] = str(cls.port)
        project_root = Path(__file__).resolve().parents[1]
        cls.server = subprocess.Popen(
            [sys.executable, "cherokee_tts_api.py"],
            cwd=project_root,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                raise RuntimeError("Cherokee TTS server exited before becoming healthy")
            try:
                with urlopen(f"{cls.base_url}/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except (OSError, URLError):
                time.sleep(1)
        cls.server.terminate()
        cls.server.wait(timeout=10)
        raise TimeoutError("Cherokee TTS server did not become healthy within 15 minutes")

    @classmethod
    def tearDownClass(cls):
        if cls.server.poll() is None:
            cls.server.terminate()
            cls.server.wait(timeout=30)

    def test_lowercase_cherokee_text_returns_wav(self):
        request = Request(
            f"{self.base_url}/synthesize",
            data=json.dumps({"text": "gadō ű:sdi?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=300) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "audio/wav")
            audio = response.read()

        with wave.open(io.BytesIO(audio), "rb") as generated:
            self.assertEqual(generated.getframerate(), 48000)
            self.assertGreater(generated.getnframes(), 0)