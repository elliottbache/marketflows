# docker/server.Dockerfile
FROM python:3.11-slim

WORKDIR /app

# copy Python package source
COPY . .

# optional deps
COPY pyproject.toml README.md ./

# install the project (creates marketflows in PATH)
RUN pip install --no-cache-dir .

# run program
CMD ["marketflows"]

