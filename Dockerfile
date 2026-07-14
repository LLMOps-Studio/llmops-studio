# =============================================================================
# LLMOps Platform - Shared Python Service Image
#
# WHY THIS EXISTS
# Every lab (rag/promptops/schema/review/memory) plus studio-core was being
# built as its OWN image from the monorepo root. Each of those builds
# independently resolved and installed the same heavy stack (chromadb,
# mlflow, langchain, langgraph) -> ~3GB per image x 6 images, and every
# `docker compose build` re-did that work from scratch with nothing shared.
#
# FIX
# One image. llmops-common + every lab + llmops-studio are installed into
# the SAME site-packages, pulled straight from GitHub (no local monorepo
# COPY, no build context dependency at all -- this Dockerfile is fully
# self-contained). docker-compose.yml then runs SIX containers off this ONE
# image, each started with a different `command:` (different uvicorn app
# target). Docker only stores the image layers once; six running
# containers share them.
#
# SELECTING LABS
# INCLUDE_LABS controls what gets installed at build time (comma-separated
# subset of: rag,promptops,schema,review,memory). Studio itself declares a
# hard pyproject dependency on all five labs, so if you ever build a
# studio-less variant you're free to trim this list; as long as
# llmops-studio is being installed, keep the full set or the pip resolve
# for llmops-studio will fail on a missing sibling package.
# =============================================================================

ARG GIT_ORG=LLMOps-Studio
ARG GIT_REF=main
ARG INCLUDE_LABS="rag,promptops,schema,review,memory"
ARG INCLUDE_STUDIO="true"

# =========================
# Builder
# =========================
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG GIT_ORG
ARG GIT_REF
ARG INCLUDE_LABS
ARG INCLUDE_STUDIO

WORKDIR /build

# 1. llmops-common first -- every lab and studio depend on it.
RUN pip install --no-cache-dir --user \
    "llmops-common @ git+https://github.com/${GIT_ORG}/LLMOpsCommon.git@${GIT_REF}#subdirectory=llmops-common"

# 2. Labs, selected via INCLUDE_LABS. Order doesn't matter between labs,
#    only that they land in site-packages before llmops-studio installs.
RUN set -eu; \
    IFS=','; \
    for lab in ${INCLUDE_LABS}; do \
      case "$lab" in \
        rag) url="rag-benchmark-lab @ git+https://github.com/${GIT_ORG}/RAGBenchmarkLab.git@${GIT_REF}#subdirectory=rag-benchmark-lab" ;; \
        promptops) url="promptops-lab @ git+https://github.com/${GIT_ORG}/PromptOpsLab.git@${GIT_REF}#subdirectory=promptops-lab" ;; \
        schema) url="schema-lab @ git+https://github.com/${GIT_ORG}/SchemaLab.git@${GIT_REF}#subdirectory=schema-lab" ;; \
        review) url="review-lab @ git+https://github.com/${GIT_ORG}/ReviewLab.git@${GIT_REF}#subdirectory=review-lab" ;; \
        memory) url="memory-lab @ git+https://github.com/${GIT_ORG}/MemoryLab.git@${GIT_REF}#subdirectory=memory-lab" ;; \
        "") continue ;; \
        *) echo "Unknown lab '$lab' in INCLUDE_LABS" >&2; exit 1 ;; \
      esac; \
      echo "Installing lab: $lab"; \
      pip install --no-cache-dir --user "$url"; \
    done

# 3. Studio itself (imports all labs -> must come last). --no-deps because
#    its pyproject lists sibling packages by bare name (e.g. "memory-lab")
#    with no PyPI-installable spec; pip already finds them satisfied from
#    step 2 in a normal install, but --no-deps makes that explicit instead
#    of relying on resolver behavior, and keeps this step skippable.
RUN if [ "${INCLUDE_STUDIO}" = "true" ]; then \
      pip install --no-cache-dir --user --no-deps \
        "llmops-studio @ git+https://github.com/${GIT_ORG}/LLMOpsStudio.git@${GIT_REF}#subdirectory=llmops-studio" && \
      pip install --no-cache-dir --user fastapi uvicorn "pydantic>=2.0.0" pyyaml python-dotenv "mlflow>=2.15,<3"; \
    fi

# =========================
# Runtime
# =========================
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY entrypoint.sh /entrypoint.sh

ENV PATH=/root/.local/bin:$PATH
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]