FROM python:3.12-slim-bookworm
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY . /app

RUN uv venv
RUN uv pip install .
ENV PATH=$PATH:/app/.venv/bin

EXPOSE 8501

CMD ["zsim", "run"]
