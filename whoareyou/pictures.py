"""Pictures for the pausing sitter (D-070, D-071).

After the opening answer, a small model picks one concrete, picturable word
from it. Openverse is searched for that word, public-domain and CC0 only. Each
candidate is downloaded (images only, size-limited, into the run's own
pictures/ folder; nothing downloaded is ever run) and screened by a small model
that can see images: no people, faces, body parts, writing, or anything
disturbing. The first that passes is used. Nothing about Robert or the project
is sent anywhere: only the search word.
"""
from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

UA = {"User-Agent": "who-are-you-experiment/0.1"}   # generic; no contact details
MAX_BYTES = 3_000_000
MAGIC = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF8": "image/gif", b"RIFF": "image/webp"}

PICK = ("From the text below, pick one concrete, physical object that could be photographed "
        "on its own, without people, such as a match, a map, a page, a leaf or a stone. Use "
        "only something the text itself mentions or clearly names. Reply with JSON only: "
        '{"word": <the word as it appears in the text, or null if there is none>, '
        '"query": <a 1-3 word image search for a plain photo of that object alone>}. Text: ')
SCREEN = ("Answer YES or NO only. Does this image show any of: a person, a face, a body part, "
          "letters, numbers, words, signs or other writing, a logo, or anything violent, "
          "medical, sexual or disturbing?")


def _media_type(data: bytes) -> Optional[str]:
    for k, v in MAGIC.items():
        if data.startswith(k):
            return v
    return None


def pick_word(client, model: str, opening: str, cost_cb) -> Optional[dict]:
    r = client.messages.create(model=model, max_tokens=200, output_config={"effort": "low"},
                               messages=[{"role": "user", "content": PICK + opening}])
    cost_cb(r)
    txt = "".join(b.text for b in r.content if b.type == "text").strip()
    try:
        j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except Exception:
        return None
    if not j.get("word") or j["word"].lower() not in opening.lower():
        return None
    return {"word": j["word"], "query": j.get("query") or j["word"]}


def find_picture(client, model: str, query: str, folder: Path, cost_cb, tries: int = 8) -> dict:
    """Returns {"ok": bool, "path", "media_type", "source", "license", "title", "screened": [...]}."""
    folder.mkdir(parents=True, exist_ok=True)
    q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "page_size": 20})
    req = urllib.request.Request("https://api.openverse.org/v1/images/?" + q, headers=UA)
    results = json.load(urllib.request.urlopen(req, timeout=30)).get("results", [])
    screened = []
    for i, res in enumerate(results[:tries]):
        url = res.get("thumbnail") or res.get("url")
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read(MAX_BYTES + 1)
        except Exception as e:
            screened.append({"source": res.get("foreign_landing_url"), "result": f"download failed: {e}"[:120]})
            continue
        mt = _media_type(data)
        if len(data) > MAX_BYTES or not mt:
            screened.append({"source": res.get("foreign_landing_url"), "result": "not an image or too large"})
            continue
        r = client.messages.create(model=model, max_tokens=10, output_config={"effort": "low"},
                                   messages=[{"role": "user", "content": [
                                       {"type": "image", "source": {"type": "base64", "media_type": mt,
                                                                    "data": base64.b64encode(data).decode()}},
                                       {"type": "text", "text": SCREEN}]}])
        cost_cb(r)
        verdict = "".join(b.text for b in r.content if b.type == "text").strip().upper()
        entry = {"source": res.get("foreign_landing_url"), "image_url": url, "license": res.get("license"),
                 "title": res.get("title"), "creator": res.get("creator"), "screen": verdict[:10]}
        screened.append(entry)
        if verdict.startswith("NO"):
            ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}[mt]
            path = folder / f"picture_{i}{ext}"
            path.write_bytes(data)
            return {"ok": True, "path": str(path), "media_type": mt, **entry, "screened": screened}
    return {"ok": False, "screened": screened}


def image_block(path: str, media_type: str) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                        "data": base64.b64encode(Path(path).read_bytes()).decode()}}
