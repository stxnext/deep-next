FROM python:3.11-slim

RUN \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      make \
      curl \
      openssh-client  \
      git \
      ca-certificates

RUN \
    git config --global user.email "deepnext@stxnext.pl" && \
    git config --global user.name "DeepNext"

WORKDIR /deep-next

# Add local bin to PATH for poetry use
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.2 python3 -
ENV PATH="/root/.local/bin:$PATH"

ARG DOT_ENV_CONTENT
RUN echo "$DOT_ENV_CONTENT" > /deep-next/.env

COPY ../.. /deep-next

RUN make install_venv

CMD ["make", "app_run"]
