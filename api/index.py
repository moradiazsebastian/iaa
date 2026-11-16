"""Entrypoint de Vercel: expone la API definida en src/foco_social/api.py.

Vercel busca este archivo (api/index.py) y sirve la variable `app`. El paquete vive en
src/, así que se agrega esa carpeta al path por si Vercel no lo instala como paquete.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from foco_social.api import app

__all__ = ["app"]
