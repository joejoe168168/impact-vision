# Impact Vision web app — chat UI, tool console and REST API on one port.
#
#   docker run -p 8787:8787 -e IMPACT_VISION_API_KEY=$(openssl rand -hex 24) \
#     -v iv-data:/home/iv/.openharness ghcr.io/<owner>/impact-vision
#
# Without IMPACT_VISION_API_KEY the server mints a one-time login token and
# prints the URL (it binds beyond loopback inside the container).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd --create-home --uid 10001 iv
WORKDIR /app
COPY pyproject.toml README.md LICENSE* ./
COPY src ./src
COPY data ./data
# The wheel bundles the terminal UI sources (force-include in pyproject.toml).
COPY frontend/terminal/package.json frontend/terminal/tsconfig.json ./frontend/terminal/
COPY frontend/terminal/src ./frontend/terminal/src
RUN pip install ".[web,office,assurance]" && rm -rf /root/.cache

USER iv
WORKDIR /home/iv/workspace
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health')"
CMD ["impact-vision", "serve-web", "--host", "0.0.0.0", "--port", "8787"]
