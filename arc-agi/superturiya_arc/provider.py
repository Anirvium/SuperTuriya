from __future__ import annotations

import base64
import io
import json
import threading
import time
import urllib.error
import urllib.request

from .config import Config


class ProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("local inference redirects are disabled")


class LocalModel:
    def __init__(self, config: Config):
        if not config.model:
            raise ValueError("model profiles require a served local model name")
        self.config = config
        # Never consult proxy env vars or send credentials.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.calls = 0
        self.tokens = {"prompt_tokens": 0, "completion_tokens": 0}
        self._stats_lock = threading.Lock()

    def complete(self, messages, timeout):
        with self._stats_lock:
            self.calls += 1  # Failed calls consume the budget too.
            call_number = self.calls
        body = {"model": self.config.model, "messages": messages,
                "max_tokens": self.config.max_tokens, "temperature": self.config.temperature,
                "top_p": self.config.top_p, "top_k": self.config.top_k,
                "seed": self.config.seed + call_number}
        if self.config.enable_thinking is not None:
            body["chat_template_kwargs"] = {"enable_thinking": self.config.enable_thinking}
        request = urllib.request.Request(self.config.endpoint.rstrip("/") + "/chat/completions",
                                         data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
        start = time.monotonic()
        try:
            with self.opener.open(request, timeout=min(timeout, self.config.request_seconds)) as response:
                payload = json.loads(response.read(2_000_000))
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("model returned no textual final response")
            usage = payload.get("usage") or {}
            with self._stats_lock:
                for key in self.tokens:
                    self.tokens[key] += int(usage.get(key, 0))
            return content, {"usage": usage, "seconds": time.monotonic()-start,
                             "model": payload.get("model", self.config.model)}
        except (OSError, ValueError, KeyError, IndexError) as exc:
            # Avoid exposing provider response bodies or local configuration secrets.
            raise ProviderError(f"local inference failed ({type(exc).__name__})") from exc


def parse_response(content):
    content = content.strip()
    if content.startswith("<think>") and "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1])
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("model response must be a JSON object")
    return payload


def grid_image(grid):
    """Optional image representation in addition to the exact integer grid."""
    from PIL import Image
    palette = [(0,0,0),(0,116,217),(255,65,54),(46,204,64),(255,220,0),(170,170,170),
               (240,18,190),(255,133,27),(127,219,255),(135,12,37),(255,255,255),
               (100,100,100),(120,70,180),(40,140,140),(180,140,80),(210,180,230)]
    img = Image.new("RGB", (len(grid[0]), len(grid)))
    img.putdata([palette[c] for row in grid for c in row])
    img = img.resize((img.width*6, img.height*6), Image.Resampling.NEAREST)
    stream = io.BytesIO()
    img.save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode()
