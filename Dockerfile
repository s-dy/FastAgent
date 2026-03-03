FROM docker.1ms.run/library/python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY server.py crawler.py ./

EXPOSE 8000

CMD ["uv", "run", "python", "server.py"]
