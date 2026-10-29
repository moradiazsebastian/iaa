"""Acceso al LLM vía LangChain, con salida estructurada y caché en disco.

El proveedor se elige con LLM_PROVIDER, así cada integrante usa la API key que tenga.
La caché hace que re-ejecutar sobre los mismos datos devuelva exactamente las mismas
respuestas (los modelos actuales no aceptan temperature=0, así que esta es la vía
para obtener resultados reproducibles).
"""

import hashlib
import json
import logging
from typing import TypeVar

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from foco_social.config import Settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLM:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.llm_provider != "none"
        self.calls = 0
        self.cache_hits = 0
        self._cache_dir = settings.cache_dir / "llm"
        self._model = self._build() if self.enabled else None

    def _build(self):
        s = self.settings
        kwargs = {}
        if s.llm_provider == "anthropic":
            kwargs["max_tokens"] = 16000
            if s.llm_effort:
                kwargs["effort"] = s.llm_effort
        elif s.llm_provider == "ollama":
            # Los modelos locales sí aceptan temperatura 0 y semilla
            kwargs.update(temperature=0, seed=s.seed, num_ctx=s.llm_num_ctx)
        if s.llm_base_url:
            kwargs["base_url"] = s.llm_base_url
        return init_chat_model(s.llm_model, model_provider=s.llm_provider, **kwargs)

    def structured(self, schema: type[T], system: str, user: str) -> T:
        """Llama al modelo y devuelve una instancia validada de `schema`."""
        if not self.enabled:
            raise RuntimeError("LLM deshabilitado (LLM_PROVIDER=none)")

        key = self._cache_key(schema, system, user)
        path = self._cache_dir / f"{key}.json"
        if self.settings.llm_cache and path.exists():
            self.cache_hits += 1
            return schema.model_validate_json(path.read_text(encoding="utf-8"))

        self.calls += 1
        log.info("LLM call #%d (%s)", self.calls, schema.__name__)
        runnable = self._model.with_structured_output(schema, method="json_schema")
        result = runnable.invoke([("system", system), ("human", user)])

        if self.settings.llm_cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result.model_dump_json(), encoding="utf-8")
        return result

    def _cache_key(self, schema: type[BaseModel], system: str, user: str) -> str:
        s = self.settings
        payload = json.dumps(
            [s.llm_provider, s.llm_model, s.llm_effort, schema.model_json_schema(), system, user],
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
