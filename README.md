# DeepNext

Your AI-powered junior software engineering assistant that takes an issue description and converts it into a pull request.

DeepNext is an advanced AI system that automatically analyzes a code repository, prepares a solution plan, and implements the necessary code for software engineering tasks using Large Language Models, saving developers hours of repetitive work.

See [documentation](https://stxnext.github.io/deep-next/) for more information.

## Quick start

[Getting Started](https://stxnext.github.io/deep-next/getting-started.html)

## GitHub/GitLab integration

Running as a service to automatically process issues:

[See integration details](https://stxnext.github.io/deep-next/integration.html)

## Configuration

DeepNext supports multiple LLM providers:
- OpenAI
- AWS Bedrock (Claude, Mistral, and others)

Create an `llm-config.yaml` file based on the example provided to configure model preferences for each pipeline stage.

For tracking and metrics, DeepNext integrates with LangSmith. Set up your credentials in the `.env` file.

[See configuration details](https://stxnext.github.io/deep-next/configuration.html)

## LangGraph Studio
You can view Deep Next workflow graph in LangGraph Studio, to do this invoke in a console:
```
langgraph dev
```
It will redirect you to [LangSmith UI](https://smith.langchain.com/), log in and you can see the graph.

## Roadmap

- **May 2025**: First public release (for registered STX Next employees)
- **June 2025**: Open-source

## Why choose DeepNext?

- **End-to-End Automation**: Complete pipeline from issue to merge request
- **Multiple LLM Support**: Works with various models to fit your needs
- **Flexible Integration**: Compatible with GitHub, GitLab and AWS
- **Customizable**: Configure different models for different pipeline stages
- **Modular**: Easy to modify, test, and improve by swapping small pieces of code
- **Open Source**: MIT-licensed and community-driven
