# NixOS Cherokee TTS

This module runs the IMS-Toucan Cherokee model as a Podman-managed HTTP service. It exposes `POST /synthesize`, accepts a JSON `text` field in the project's Latin/MCO Cherokee orthography, and returns generated WAV audio. Lowercase text is supported: the text frontend lowercases MCO before converting it to phones, and `tests/test_cherokee_case.py` checks lowercase/uppercase equivalence.

The model checkpoints are from the `2022.07.18.01` release. On first start, systemd builds the container image and the service downloads the FastSpeech2 and HiFi-GAN checkpoints into `/var/lib/cherokee-toucan/Models`. Those files persist across container rebuilds. The first start needs network access and about 620 MB for the checkpoints, in addition to the container image.

Import the module from your NixOS configuration and enable it:

```nix
{
  imports = [ /path/to/IMS-Toucan-Cherokee/nix/module.nix ];

  services.cherokeeToucan = {
    enable = true;
    # Optional; these are the defaults.
    bindAddress = "127.0.0.1";
    port = 8765;
  };
}
```

Rebuild and start the service with `sudo nixos-rebuild switch`. The module enables Podman, and systemd builds the image from this checkout when the service starts. Use a checkout of the desired IMS-Toucan source revision; the model URLs are pinned to release `2022.07.18.01`.

Submit text and save the response as WAV:

```sh
curl --fail-with-body http://127.0.0.1:8765/synthesize \
  -H 'Content-Type: application/json' \
  --data '{"text":"gadō ű:sdi?"}' \
  --output cherokee.wav
```

`GET /health` reports readiness after model loading. The default listener is localhost-only. The endpoint has no authentication, so do not bind it to a public interface without putting an authenticated, rate-limited reverse proxy in front of it. The service handles the project's Latin/MCO Cherokee input; it does not transliterate Cherokee syllabary text.
