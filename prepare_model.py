"""Download a fixed, checksummed ONNX model. No remote Python code is executed."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
REPO = "onnx-community/house-plant-image-detection-ONNX"
REVISION = "24d519d5ce1dd1a44b159b4e1bef012d01f30b95"
FILES = {"config.json": "config.json", "preprocessor_config.json": "preprocessor_config.json",
         "onnx/model_quantized.onnx": "model_quantized.onnx"}
HASHES = {
    "config.json": "84f0eca9e417d8df7b5be366d1876e9edf560fd23d1a5c10b1a86ac8108c1190",
    "preprocessor_config.json": "445c77049d082004aa07593344d5e1f521f1198228bf586196f70ce7ae021414",
    "model_quantized.onnx": "d746a150317b670ed308c243b4aba46f1c0e69c5d1da68e7713b8aca72097c0b",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare():
    MODEL_DIR.mkdir(exist_ok=True)
    base = f"https://huggingface.co/{REPO}/resolve/{REVISION}/"
    # Model digest was verified against the immutable revision's LFS metadata.
    # Pin metadata too so rerunning repairs corrupt configuration and works offline
    # when every file is already present and valid.
    for remote, local in FILES.items():
        target = MODEL_DIR / local
        if target.exists() and digest(target) == HASHES[local]:
            print(f"Already prepared: {local}", flush=True)
            continue
        temporary = target.with_suffix(target.suffix + ".part")
        print(f"Downloading {remote} ...", flush=True)
        try:
            with urllib.request.urlopen(base + remote, timeout=180) as source, temporary.open("wb") as dest:
                while chunk := source.read(1024 * 1024):
                    dest.write(chunk)
            if digest(temporary) != HASHES[local]:
                raise RuntimeError(f"SHA-256 verification failed for {local}; refusing to use it.")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    manifest = {"repository": REPO, "revision": REVISION,
                "model_sha256": HASHES["model_quantized.onnx"], "bytes": (MODEL_DIR / "model_quantized.onnx").stat().st_size,
                "license": "Apache-2.0"}
    (MODEL_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    prepare()
