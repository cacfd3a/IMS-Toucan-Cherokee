# Run the Cherokee text-to-speech HTTP API, loading the required models on startup.
import hashlib
import json
import os
import tempfile
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from InferenceInterfaces.InferenceFastSpeech2 import InferenceFastSpeech2


RELEASE = "2022.07.18.01"
MODELS = {
    "FastSpeech2_Cherokee_West/best.pt": {
        "urls": (
            f"https://github.com/CherokeeLanguage/IMS-Toucan/releases/download/{RELEASE}/"
            "FastSpeech2_Cherokee_West-best.pt",
            "https://nativeamerican.blackenvelope.net/FastSpeech2_Cherokee_West-best.pt",
        ),
        "sha256": "70ad6d4d517dbc0eb5adeac764dd5427a76eaa813309b190d2b712e09c74522e",
    },
    "HiFiGAN_combined/best.pt": {
        "urls": (
            f"https://github.com/CherokeeLanguage/IMS-Toucan/releases/download/{RELEASE}/"
            "HiFiGAN_combined-best.pt",
            "https://nativeamerican.blackenvelope.net/HiFiGAN_combined-best.pt",
        ),
        "sha256": "56b8c18a272f66c0cbf9104c4251b06c3be81b306c85be968429fbc1634d1690",
    },
}
MAX_REQUEST_BYTES = 64 * 1024
MAX_TEXT_CHARS = 2000
MODEL_LOCK = threading.Lock()


def ensure_models():
    for relative_path, model in MODELS.items():
        destination = Path("Models") / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = destination.with_suffix(destination.suffix + ".download")
        expected_sha256 = model["sha256"]
        if destination.is_file():
            digest = hashlib.sha256()
            with destination.open("rb") as existing:
                for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() == expected_sha256:
                continue
            print(f"Existing model {destination} failed SHA-256 validation; replacing it", flush=True)

        failures = []
        for url in model["urls"]:
            print(f"Downloading {destination} from {url}", flush=True)
            try:
                digest = hashlib.sha256()
                with urlopen(url, timeout=120) as response, temporary_path.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                        digest.update(chunk)
                actual_sha256 = digest.hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ValueError(
                        f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {actual_sha256}"
                    )
                os.replace(temporary_path, destination)
                break
            except Exception as error:
                temporary_path.unlink(missing_ok=True)
                failures.append(f"{url}: {error}")
        else:
            raise RuntimeError(
                f"Could not download a verified copy of {destination}: {'; '.join(failures)}"
            )


def normalize_text(text):
    return unicodedata.normalize("NFC", text).lower()


class CherokeeTTSHandler(BaseHTTPRequestHandler):
    tts = None

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"status":"ready"}')

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self.send_error(413, "Request body must be between 1 byte and 64 KiB")
            return

        try:
            request = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "Expected a UTF-8 JSON request")
            return
        text = request.get("text") if isinstance(request, dict) else None
        if not isinstance(text, str) or not text.strip():
            self.send_error(400, 'JSON field "text" must be a non-empty string')
            return
        if len(text) > MAX_TEXT_CHARS:
            self.send_error(413, "Text must be at most 2000 characters")
            return

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output:
                temporary_path = output.name
            with MODEL_LOCK:
                self.tts.read_to_file([normalize_text(text)], temporary_path, silent=True)
            with open(temporary_path, "rb") as audio:
                audio_data = audio.read()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio_data)))
            self.end_headers()
            self.wfile.write(audio_data)
        except Exception:
            self.log_error("Speech synthesis failed")
            self.send_error(500, "Speech synthesis failed")
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)


def main():
    ensure_models()
    CherokeeTTSHandler.tts = InferenceFastSpeech2(device="cpu", model_name="Cherokee_West")
    CherokeeTTSHandler.tts.set_language("chr")
    host = os.environ.get("TOUCAN_HOST", "0.0.0.0")
    port = int(os.environ.get("TOUCAN_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), CherokeeTTSHandler)
    print(f"Cherokee TTS listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()