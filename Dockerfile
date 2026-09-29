# Community image. No distro-specific Revel package.
FROM python:3.12-slim-bookworm

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir -e '.[web]'

ENV REVEL_STORE_ENGINE=file
EXPOSE 8000
ENTRYPOINT ["revelctl"]
CMD ["--help"]
