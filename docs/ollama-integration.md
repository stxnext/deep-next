# Ollama Integration

This document explains how to use local LLMs with Ollama in the Deep Next project.

## Prerequisites

1. Install Ollama on your system: https://ollama.com/download


## Running Ollama

Before using Ollama models, make sure the Ollama service is running:

```bash
# Start the Ollama service
ollama serve

# In another terminal, pull the models you need
ollama pull gemma3:27b-it-qat
ollama pull deepcoder
```

## Configuration

Add an Ollama configuration section to your `llm-config.yaml` file:

```yaml
ollama-example:
  model: codellama
  seed: 42  # Optional
  temperature: 0.7
```

## Available Models

The following Ollama models are added to deepnext:

- `gemma:4b`
- `gemma3:12b`
- `gemma3:27b-it-qat`
- `gemma3:12b-it-qat`
- `codellama:python`
- `deepcoder`
- `qwen3:8b`

You can add more models by extending the class `Model` in the `libs/common/deep_next/common/llm.py` module.


## Performance Considerations

- Local LLMs have worse performance characteristics than cloud-based models
- Some advanced features like tools/function calling may not be supported by all models. You can check it on the model ollama page.


## Checked models

| Model | parameters | Comment |
|:------:|:------:|:------:|
| qwen3:4b, qwen3:8b, gemma3:4b,  gemma3:4b-it-qat      | 8B <   | Models are able to generate project description, but is not able to properly call tools for ACR
| codellama:python | 7B | Model used only for implementation phase. Model was not able to generate response in a given format <original></original><patched></patched> |
| deepcoder | 14B |  Model used only for implementation phase. Model based on Qwen (finetuned from Deepseek-R1-Distilled-Qwen-14B via distributed RL). It was not able to fit to the implement output format. |
| gemma3:12b, gemma3:27b-it-qat, gemma3:12b-it-qat | 12B, 27B | All Gemma 12B and 27B models have a very similar response. They never called up any tool. Sometimes he was able to specify some files in ACR, but he did so based only on the prompt. Often gave examples from example as responses. Sometimes it would generate the correct implementation format. |
