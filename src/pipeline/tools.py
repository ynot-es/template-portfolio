"""Function-calling / tool-use — registro de tools usadas pelo agente.

Reaproveita o LAB-001. Voce vai preencher 1 TODO aqui (sua tool especifica).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any, Callable


# ============================================================================
# TODO 4 — Sua tool especifica do dominio
# ============================================================================


def run_linter(code: str) -> str:
    """Roda ruff check no snippet de codigo Python e retorna os erros encontrados.

    Usa arquivo temporario — nunca usa eval() ou exec() por seguranca.
    """
    if not code or not code.strip():
        return "Nenhum codigo fornecido."

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=text", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip().replace(tmp_path, "snippet.py")
        return output if output else "Nenhuma violacao encontrada pelo ruff."
    except FileNotFoundError:
        return "ruff nao instalado. Execute: pip install ruff"
    except subprocess.TimeoutExpired:
        return "Timeout: linter demorou mais de 10s."
    finally:
        os.unlink(tmp_path)


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_linter",
            "description": (
                "Executa o linter ruff check em um snippet de codigo Python. "
                "Use sempre que o usuario enviar codigo para revisao."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Snippet de codigo Python a ser verificado.",
                    }
                },
                "required": ["code"],
            },
        },
    },
]


TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "run_linter": run_linter,
}


def run_tool_call(name: str, arguments_json: str) -> str:
    """Executa uma tool call e retorna o resultado como string."""
    if name not in TOOL_REGISTRY:
        return f"ERROR: tool '{name}' nao registrada"
    try:
        kwargs = json.loads(arguments_json)
        return TOOL_REGISTRY[name](**kwargs)
    except Exception as e:
        return f"ERROR ao executar {name}: {e}"