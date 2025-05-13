---
layout: default
title: Integration
---

# Integration

DeepNext can be integrated with GitHub and GitLab to automatically process issues and create pull/merge requests.

## GitHub/GitLab Integration

Running as a service to automatically process issues:

```bash
# Start the DeepNext app in Docker
make app_docker_run
```

## GitHub Integration

```dotenv
# VCS connector setup (required to connect core pipeline with VCS)
VCS_PROVIDER=github
VCS_ACCESS_TOKEN=<your GitHub access token>
VCS_REPO_PATH=stxnext/deep-next
```

## Configuration for GitLab

```dotenv
# VCS connector setup (required to connect core pipeline with VCS)
VCS_PROVIDER=gitlab
VCS_ACCESS_TOKEN=<your GitLab access token>
VCS_REPO_PATH=stxnext/deep-next
```

## How It Works

1. DeepNext listens for new issues with a specified label
2. When matching issues are found, they are processed through the pipeline
3. A pull/merge request is created with the implemented solution
4. Status updates are posted as comments on the original issue

[Back to Home](./index.html)
