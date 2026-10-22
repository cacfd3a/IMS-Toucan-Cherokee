import hashlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

from cherokee_tts_api import ensure_models


class ModelDownloadTest(unittest.TestCase):
    def test_uses_verified_mirror_when_primary_fails(self):
        model_bytes = b"verified model checkpoint"
        model = {
            "urls": ("https://primary.example/model.pt", "https://mirror.example/model.pt"),
            "sha256": hashlib.sha256(model_bytes).hexdigest(),
        }

        with tempfile.TemporaryDirectory() as directory:
            previous_directory = os.getcwd()
            os.chdir(directory)
            self.addCleanup(os.chdir, previous_directory)

            with patch("cherokee_tts_api.MODELS", {"test/model.pt": model}), patch(
                "cherokee_tts_api.urlopen",
                side_effect=(OSError("primary unavailable"), io.BytesIO(model_bytes)),
            ):
                ensure_models()

            with open("Models/test/model.pt", "rb") as downloaded:
                self.assertEqual(downloaded.read(), model_bytes)

    def test_rejects_models_that_fail_hash_validation(self):
        model = {
            "urls": ("https://primary.example/model.pt", "https://mirror.example/model.pt"),
            "sha256": hashlib.sha256(b"expected model").hexdigest(),
        }

        with tempfile.TemporaryDirectory() as directory:
            previous_directory = os.getcwd()
            os.chdir(directory)
            self.addCleanup(os.chdir, previous_directory)

            with patch("cherokee_tts_api.MODELS", {"test/model.pt": model}), patch(
                "cherokee_tts_api.urlopen",
                side_effect=(io.BytesIO(b"corrupt primary"), io.BytesIO(b"corrupt mirror")),
            ):
                with self.assertRaisesRegex(RuntimeError, "Could not download a verified copy"):
                    ensure_models()

            self.assertFalse(os.path.exists("Models/test/model.pt"))
