# MentAI: Code Review & Compliance Python

* Dupla: Maria Leticia de Oliveira Cardoso º Tony Esau de Oliveira

>  Assistente inteligente que revisa código Python e verifica conformidade com o Google Python Style Guide, combinando RAG, análise estática com `ruff` e model routing para desenvolvedores que querem escrever código mais limpo.

<!-- TODO: cole aqui o GIF de demo (10-15s, <5MB) gerado com peek/terminalizer/OBS -->

**Live demo:** TODO — substitua pelo link do Streamlit Cloud / HuggingFace Spaces / FastAPI

## Problem statement

1. Qual problema voce resolve?

    Desenvolvedores Python perdem tempo em code reviews manuais verificando conformidade com style guides extensos como o Google Python Style Guide.

2. Para quem?

    Para times de desenvolvimento Python que precisam manter consistência de código sem depender de revisores humanos para cada PR.

3. Por que LLM + RAG + Tool-use eh a abordagem certa (vs. busca simples)?

    LLM + RAG é a abordagem certa porque o style guide é um corpus textual denso com regras interdependentes — busca simples retorna trechos sem contexto; o LLM sintetiza as regras relevantes e as aplica ao código submetido. A tool `run_linter` complementa com análise determinística via `ruff`, combinando o melhor dos dois mundos.
## Arquitetura

```mermaid
flowchart LR
    USER([User]) --> UI[Streamlit UI]
    UI --> CACHE{Exact cache?}
    CACHE -->|hit| RESP[Response]
    CACHE -->|miss| SEM{Semantic cache?}
    SEM -->|hit| RESP
    SEM -->|miss| CLS[Classify complexity]
    CLS -->|simple| CHEAP[gemini-2.5-flash-lite]
    CLS -->|complex| ORCH[Orchestrator]
    ORCH --> RAG[(Chroma RAG\nGoogle Style Guide)]
    ORCH --> TOOL[run_linter\nruff check]
    RAG --> PREMIUM[gemini-2.5-pro]
    TOOL --> PREMIUM
    PREMIUM --> RESP
```
## Setup

```bash
# 1. Clone
git clone rfdr
cd template-portfolio

# 2. Dependencias
uv venv && source .venv/bin/activate
uv sync

# 3. API key
cp .env.example .env
# edite .env com sua GEMINI_API_KEY

# 4. Corpus
# Coloque o Google Python Style Guide em PDF em data/corpus/
# Download: https://google.github.io/styleguide/pyguide.html → Ctrl+P → Salvar PDF

# 5. Rodar local
streamlit run src/ui/streamlit_app.py
```

## Cost & Latency

TODO — preencher apos rodar bench de 50 queries (veja notebook 05).

| Estrategia | Custo total | Reducao | P95 latency |
|---|---:|---:|---:|
| Baseline (premium sempre) | $X.XX | — | XX ms |
| + Exact cache | $X.XX | XX% | XX ms |
| + Semantic cache | $X.XX | XX% | XX ms |
| **+ Routing cheap-first** | **$X.XX** | **XX%** | **XX ms** |

Meta da rubrica (banda "excelente"): **≥50% de reducao** + P95 reportado.

## Design decisions

- **Embedding model `gemini-embedding-001`:** escolhido por ser gratuito no free tier e ter boa performance em texto técnico em inglês — o corpus do Google Style Guide é inteiramente em inglês.
- **`chunk_size=800, overlap=100`:** o Style Guide tem seções de Decision (~300-600 chars) e exemplos de código (~200-400 chars). Chunks de 800 capturam seção + exemplo sem fragmentar o raciocínio; overlap de 100 evita cortar frases no meio.
- **Tool `run_linter` com `ruff`:** `ruff` é 10-100x mais rápido que `pylint` e `flake8`, tem output limpo e é o padrão emergente. Usamos `subprocess` com arquivo temporário — nunca `eval()` — por segurança.
- **Tradução da query antes do retrieval:** o corpus está em inglês; perguntas em português têm similaridade cosseno baixa contra os chunks. A tradução via LLM antes do `retrieve()` aumenta significativamente a qualidade do contexto recuperado.
- **Sem re-ranking:** corpus pequeno (~100 chunks), latência é mais crítica que precisão marginal de re-ranking. Top-5 por similaridade cosseno é suficiente.


## Limitations

- O corpus cobre apenas o Google Python Style Guide — não inclui PEP 8 completo, guias de frameworks como Django ou FastAPI, ou convenções de outros times.
- O free tier do Gemini limita a 100 requests/min para embeddings — a indexação inicial requer `time.sleep(6)` entre batches e leva ~3-5 minutos.
- A demo não suporta upload de PDF pelo usuário — o corpus é fixo. Para usar outro style guide seria necessário reindexar manualmente.


## Tech stack

- **LLM:** Gemini 2.5 Flash-Lite (cheap) / Gemini 2.5 Pro (premium)
- **Embeddings:** gemini-embedding-001
- **Linter:** ruff (sandboxed via subprocess)
- **Vector store:** Chroma local
- **UI:** Streamlit
- **Observability:** structured logs com trace_id
- **Deploy:** Streamlit Community Cloud

## Estrutura

```
projeto-portfolio/
├── data/
│   ├── corpus/           # seus PDFs (substituir os de exemplo)
│   └── chroma/           # vector store (gitignored)
├── src/
│   ├── ui/streamlit_app.py
│   ├── pipeline/
│   │   ├── rag.py        # TODOs 1-3
│   │   ├── tools.py      # TODO 4
│   │   ├── cache.py      # TODO 5
│   │   └── routing.py    # TODO 6
│   └── observability/trace.py
├── tests/test_smoke.py
├── pyproject.toml
├── .env.example
└── README.md             # voce esta aqui
```

## Os 6 TODOs (mapa rapido)

| TODO | Arquivo | Tempo estimado | Material de referencia |
|---|---|---:|---|
| **1** | `src/pipeline/rag.py::ingest_and_index` | 20 min | notebook 02 Etapas 1+2+3 |
| **2** | `src/pipeline/rag.py::retrieve` | 5 min | notebook 02 Etapa 4 |
| **3** | `src/pipeline/rag.py::answer` | 15 min | notebook 02 Etapa 5 |
| **4** | `src/pipeline/tools.py` (sua tool) | 30 min | LAB-001 + criatividade |
| **5** | `src/pipeline/cache.py::SemanticCache.get` | 15 min | notebook 05 Etapa 4 |
| **6** | `src/pipeline/routing.py::classify_complexity` | 10 min | notebook 05 Etapa 5 |

**Total estimado:** ~1h35 dos 6 TODOs. Resto do tempo: corpus, deploy, README, polish.

## Rubrica

Veja `projeto-portfolio.pdf` (briefing do projeto) para a rubrica 3-bandas completa.

| Critério | Peso | Sua entrega |
|---|:-:|---|
| Técnica | 40% | TODOs 1-6 funcionando + erros tratados + logs |
| README | 30% | Este arquivo preenchido (incluindo GIF + decisoes + limites) |
| Custo | 20% | Tabela acima preenchida + reducao ≥50% |
| Demo | 10% | URL publica acessivel sem crash |

---


*Dupla: Maria Leticia · Tony Oliveira*

*Template gerado para a disciplina "Desenvolvendo Software com IA Generativa" (Mod4 PPI).*
