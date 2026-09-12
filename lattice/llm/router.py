import asyncio
import json
import threading
import time
from typing import Any
from utils.logger import get_logger
from config.settings import get_settings

log = get_logger("llm.router")

LLM_TIMEOUT = 120.0   # seconds — LLM calls can be slow for large prompts
EMBED_TIMEOUT = 30.0  # seconds — embeddings are fast


class LLMRouter:
    def __init__(self):
        self.settings = get_settings()
        self._ollama = None
        self._claude = None
        self._lock = threading.Lock()

    def _get_ollama(self):
        if self._ollama is None:
            with self._lock:
                if self._ollama is None:
                    import ollama
                    self._ollama = ollama
        return self._ollama

    def _get_claude(self):
        if self._claude is None:
            with self._lock:
                if self._claude is None:
                    import anthropic
                    self._claude = anthropic.Anthropic(
                        api_key=self.settings.anthropic_api_key,
                        timeout=LLM_TIMEOUT,
                    )
        return self._claude

    async def complete(
        self,
        prompt: str,
        system: str = "",
        schema: dict | None = None,
        model: str | None = None,
    ) -> str:
        backend = self.settings.llm_backend
        if backend == "ollama":
            return await self._ollama_complete(prompt, system, schema, model)
        elif backend == "claude":
            return await self._claude_complete(prompt, system)
        else:
            raise ValueError(f"Unknown LLM backend: {backend}")

    async def _ollama_complete(
        self,
        prompt: str,
        system: str,
        schema: dict | None,
        model: str | None,
    ) -> str:
        ollama = self._get_ollama()
        model = model or self.settings.ollama_primary_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if schema is not None:
            kwargs["format"] = "json"

        t0 = time.time()
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(ollama.chat, **kwargs),
                timeout=LLM_TIMEOUT,
            )
            content = resp["message"]["content"]
            log.debug(f"Ollama {model} | {len(prompt)} prompt chars | {time.time()-t0:.1f}s")
            return content
        except asyncio.TimeoutError:
            log.error(f"Ollama {model} timed out after {LLM_TIMEOUT}s")
            raise TimeoutError(f"LLM call timed out after {LLM_TIMEOUT}s")
        except Exception as e:
            log.error(f"Ollama error: {e}")
            if model != self.settings.ollama_primary_model:
                raise
            log.warning(f"Falling back to {self.settings.ollama_fallback_model}")
            kwargs["model"] = self.settings.ollama_fallback_model
            resp = await asyncio.wait_for(
                asyncio.to_thread(ollama.chat, **kwargs),
                timeout=LLM_TIMEOUT,
            )
            return resp["message"]["content"]

    async def _claude_complete(self, prompt: str, system: str) -> str:
        client = self._get_claude()
        t0 = time.time()
        kwargs: dict[str, Any] = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        resp = await asyncio.wait_for(
            asyncio.to_thread(client.messages.create, **kwargs),
            timeout=LLM_TIMEOUT,
        )
        content = resp.content[0].text
        log.debug(f"Claude | {len(prompt)} prompt chars | {time.time()-t0:.1f}s")
        return content

    async def complete_json(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        retries: int = 2,
    ) -> dict:
        """Complete and parse JSON. Retry on invalid JSON or a non-object result.

        Every caller (brain_dump, intent_planner, projects chat, wiki_compiler,
        file_ingest) does `result.get(...)` on the return value with no type
        check of its own — a model that returns valid JSON that isn't an object
        (a bare array, string, or number) used to pass straight through and
        crash deep inside whichever caller called it first. Validating the
        shape here, once, protects all of them.
        """
        for attempt in range(retries):
            raw = await self.complete(prompt, system, schema={}, model=model)
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
                return parsed
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < retries - 1:
                    log.warning(f"Invalid JSON (attempt {attempt+1}): {e}, retrying")
                    prompt = f"Your previous response was not a valid JSON object. Return ONLY a valid JSON object.\n\nOriginal task:\n{prompt}"
                else:
                    log.error(f"JSON parse failed after {retries} attempts. Raw: {raw[:200]}")
                    raise ValueError(f"LLM returned invalid JSON: {raw[:200]}")

    async def embed(self, text: str) -> list[float]:
        """Always uses Ollama nomic-embed-text, regardless of backend."""
        ollama = self._get_ollama()
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama.embeddings,
                    model=self.settings.ollama_embed_model,
                    prompt=text,
                ),
                timeout=EMBED_TIMEOUT,
            )
            return resp["embedding"]
        except asyncio.TimeoutError:
            log.error(f"Embedding timed out after {EMBED_TIMEOUT}s")
            raise
        except Exception as e:
            log.error(f"Embedding error: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


_router: LLMRouter | None = None


def get_llm() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
