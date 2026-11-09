"""Build viewer/sittings.html: every exported sitting pair on one page."""
from __future__ import annotations

import json
from pathlib import Path

from .export import pairs

TEMPLATE = Path(__file__).with_name("viewer_template.html")


def build(sittings_dir: Path, out: Path) -> int:
    ps = pairs(sittings_dir)
    data = json.dumps(ps, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.read_text().replace("__DATA__", data))
    return len(ps)
