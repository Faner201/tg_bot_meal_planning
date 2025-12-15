FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && if [ -f /root/.cargo/bin/uv ]; then ln -sf /root/.cargo/bin/uv /usr/local/bin/uv; fi \
    && if [ -f /root/.local/bin/uv ]; then ln -sf /root/.local/bin/uv /usr/local/bin/uv; fi

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests

RUN uv pip install --system -e .

CMD ["uv", "run", "python", "-m", "http.server", "8000"]


