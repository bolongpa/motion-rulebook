"""Vision-model interface for the describe stage.

The miner needs *observations*, not judgments: for each panel, the model
lists observable visual elements of how the labeled event is depicted.
FakeVisionModel is deterministic (canned descriptions) for tests and the
mechanics demo; OpenAICompatibleVisionModel does real runs against any
OpenAI-compatible chat-completions endpoint with image input.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request


class VisionModel:
    """describe() returns {actors: [...], elements: [...], note: str}."""

    def describe(self, image_path: str, event: str) -> dict:
        raise NotImplementedError


class FakeVisionModel(VisionModel):
    """Canned descriptions keyed by panel id (basename without extension)."""

    def __init__(self, descriptions: dict):
        self.descriptions = descriptions

    def describe(self, image_path: str, event: str) -> dict:
        key = os.path.splitext(os.path.basename(image_path))[0]
        if key not in self.descriptions:
            raise KeyError(f"no canned description for panel {key!r}")
        d = dict(self.descriptions[key])
        d.setdefault("actors", [])
        d.setdefault("elements", [])
        d.setdefault("note", "")
        return d


DESCRIBE_SYSTEM = (
    "You document how a canonical event is depicted in animation/manga stills. "
    "List only what is OBSERVABLE in the image about how the event is depicted. "
    "No inference, no negations, one observable fact per element. "
    'Return JSON only: {"actors": [...], "elements": [...], "note": "..."}.'
)


def describe_prompt(event: str) -> str:
    return (f"Event: {event}\n"
            f"Document how this event is depicted in this image. "
            f"Actors: who performs/is affected. Elements: short observable "
            f"phrases describing the depiction (e.g. 'cheek pouches glow "
            f"bright yellow').")


class OpenAICompatibleVisionModel(VisionModel):
    """Real VLM via an OpenAI-compatible endpoint (needs image input)."""

    def __init__(self, model: str, api_key: str | None = None,
                 base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

    def describe(self, image_path: str, event: str) -> dict:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(image_path)[1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "webp": "image/webp"}.get(
                    ext.lstrip("."), "image/png")
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": DESCRIBE_SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": describe_prompt(event)},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]},
            ],
            "temperature": 0,
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"] or ""
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                      flags=re.MULTILINE).strip()
        d = json.loads(text)
        return {"actors": d.get("actors", []),
                "elements": d.get("elements", []),
                "note": d.get("note", "")}
