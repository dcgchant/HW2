"""PowerShell: python run.py [--port 8000]. No virtual environment required."""
import argparse
from pathlib import Path
import site
import sys

ROOT = Path(__file__).resolve().parent
PACKAGES = ROOT / ".packages"
if PACKAGES.is_dir():
    site.addsitedir(str(PACKAGES))
    sys.path.insert(0, str(PACKAGES))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local CPU plant classifier")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        import uvicorn
        from app import app
    except ImportError as error:
        raise SystemExit(f"Missing dependency: {error}\nRun: python -m pip install --target .packages -r requirements.txt")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=True)
