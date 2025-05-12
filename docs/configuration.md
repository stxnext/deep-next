---
layout: default
title: Configuration
---

# Configuration

DeepNext supports multiple LLM providers and can be configured to use different models for different stages of the pipeline.

## LLM Configuration

DeepNext supports the following LLM providers:
- OpenAI
- AWS Bedrock (Claude, Mistral, and others)

Create an `llm-config.yaml` file based on the example provided to configure model preferences for each pipeline stage:

```yaml
# Example configuration - customize to your needs
provider: bedrock  # Options: openai, bedrock
model: anthropic.claude-3-sonnet-20240229-v1:0
# For different stages you can specify different models
action_plan:
  provider: openai
  model: gpt-4o
```

## Environment Variables

For tracking and metrics, DeepNext integrates with LangSmith. Set up your credentials in the `.env` file.

```
# OpenAI access
OPENAI_API_KEY=...

# AWS Bedrock access
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## Advanced Configuration

See the `llm-config-example.yaml` file for more detailed configuration options.

[Back to Home](./index.html)
