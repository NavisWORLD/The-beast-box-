import sys
from pathlib import Path

HOST = Path(__file__).resolve().parents[1]
PKG = HOST.parent
sys.path.insert(0, str(HOST))
