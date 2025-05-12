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
make app_docker_build
make app_docker_run
```

## Configuration for GitLab

```json
{
    "project_name": "deep_next",
    "gitlab": {
        "project_id": "<project_id>",
        "base_url": "<url>",
        "access_token": "<access_token>"
    },
    "git": {
        "ref_branch": "develop",
        "repo_url": "<repo_url.git>",
        "label": "git_label"
    }
}
```

## GitHub Integration

Similar configuration is available for GitHub integration, using the GitHub connector module.

## How It Works

1. DeepNext listens for new issues with a specified label
2. When matching issues are found, they are processed through the pipeline
3. A pull/merge request is created with the implemented solution
4. Status updates are posted as comments on the original issue

[Back to Home](./index.html)
