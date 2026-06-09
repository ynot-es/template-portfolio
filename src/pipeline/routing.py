"""Model routing cheap-first com fallback.

Reaproveita o notebook 05. Voce vai preencher 1 TODO aqui.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class RouteDecision:
    model: str
    complexity: str  # "simple" | "complex"
    reason: str


# ------------------------------------------------------------------ TODO 6
def classify_complexity(query: str) -> RouteDecision:
    """Classifica complexidade da query para escolher modelo (cheap vs premium).

    Estrategia heuristica simples. Em producao, evoluiria para classifier treinado.
    """
    cheap_model = os.environ.get("CHEAP_MODEL", "gemini-2.5-flash-lite")
    premium_model = os.environ.get("PREMIUM_MODEL", "gemini-2.5-pro")

    # Palavras que indicam analise profunda de codigo — roteiam para modelo premium
    complex_keywords = {
        "explique", "compare", "analise", "refatore", "otimize",
        "vulnerabilidade", "diferencie", "justifique", "avalie", "reestruture",
    }

    query_lower = query.lower()

    if any(kw in query_lower for kw in complex_keywords):
        return RouteDecision(
            model=premium_model,
            complexity="complex",
            reason="query requer analise aprofundada de codigo",
        )

    if len(query) < 60 and query.strip().endswith("?"):
        return RouteDecision(
            model=cheap_model,
            complexity="simple",
            reason="query curta e objetiva",
        )

    return RouteDecision(
        model=cheap_model,
        complexity="simple",
        reason="padrao: sem indicadores de complexidade",
    )


def make_client() -> OpenAI:
    """Cliente OpenAI-compatible para o provider configurado."""
    if "GEMINI_API_KEY" in os.environ:
        return OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return OpenAI()
