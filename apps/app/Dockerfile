FROM python:3.11-slim

RUN \
    apt-get update && \
    apt-get install -y --no-install-recommends make curl openssh-client git

RUN \
    git config --global user.email "deepnext@stxnext.pl" && \
    git config --global user.name "DeepNext"

WORKDIR /deep-next

# Add local bin to PATH for poetry use
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.2 python3 -
ENV PATH="/root/.local/bin:$PATH"

ARG DOT_ENV_CONTENT
RUN echo "$DOT_ENV_CONTENT" > /deep-next/.env

# Inject SSH private key for GitLab authentication
# TODO: Better idea might be to use AWS Secrets Manager
ARG SSH_PRIVATE_KEY
RUN mkdir -p ~/.ssh && \
    echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa && \
    chmod 600 ~/.ssh/id_rsa && \
    ssh-keyscan gitlab.com >> ~/.ssh/known_hosts && \
    ssh-keyscan -H git.stxnext.pl >> ~/.ssh/known_hosts

COPY ../.. /deep-next

RUN make install_venv

CMD ["make", "app_run"]
