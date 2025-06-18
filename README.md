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
- Ollama (for local LLM usage)

Create an `llm-config.yaml` file based on the example provided to configure model preferences for each pipeline stage. See [Ollama integration](docs/ollama-integration.md) for details on using local models.

For tracking and metrics, DeepNext integrates with LangSmith. Set up your credentials in the `.env` file.

[See configuration details](https://stxnext.github.io/deep-next/configuration.html)

## Roadmap

- **May 2025**: First public release (for registered STX Next employees)
- **June 2025**: Open-source

## Why choose DeepNext?

- **End-to-End Automation**: Complete pipeline from issue to merge request
- **Multiple LLM Support**: Works with various models to fit your needs
- **Flexible Integration**: Compatible with GitHub, GitLab and AWS
- **Customizable**: Configure different models for different pipeline stages
- **Modular**: Easy to modify, test, and improve by swapping small pieces of code

## License

This project is licensed under the **Apache License 2.0**.
See the [LICENSE](./LICENSE) file in this repository for full terms.

---

### Third-Party Licenses

This project depends on open-source libraries released under the following licenses:

---

#### [MIT License](./third_party_licenses/MIT.txt)

Deprecated, PyJWT, PyYAML, SQLAlchemy, annotated-types, anyio, appdirs, attrs, backoff, cffi, cfgv, charset-normalizer, dataclasses-json, h11, httpx-sse, identify, iniconfig, jiter, jmespath, langchain, langchain-aws, langchain-community, langchain-core, langchain-ollama, langchain-openai, langchain-text-splitters, langfuse, langgraph, langgraph-checkpoint, langgraph-prebuilt, langgraph-sdk, langsmith, libcst, loguru, markdown-it-py, marshmallow, mdurl, mypy_extensions, orjson, ormsgpack, platformdirs, pluggy, pre_commit, pydantic, pydantic-settings, pydantic_core, pyee, pyppeteer, pytest, RapidFuzz, rich, six, slack_sdk, tiktoken, typing-inspect, typing-inspection, unidiff, urllib3, virtualenv

---

#### [Apache License 2.0](./third_party_licenses/Apache-2.0.txt)

PyNaCl, aiohttp, aiosignal, boto3, botocore, cryptography, distro, frozenlist, importlib_metadata, openai, orjson, ormsgpack, packaging, propcache, requests, requests-toolbelt, s3transfer, sniffio, sortedcontainers, tenacity, yarl, regex, python-dateutil

---

#### [BSD License (BSD-3-Clause)](./third_party_licenses/BSD-3-Clause.txt)

Pygments, click, cryptography, httpcore, httpx, idna, jsonpatch, jsonpointer, nodeenv, numpy, packaging, pycparser, python-dateutil, python-dotenv, scipy, websockets, wrapt, xxhash

---

#### [Python Software Foundation License](./third_party_licenses/PSF.txt)

aiohappyeyeballs, distlib, greenlet, typing_extensions

---

#### [Mozilla Public License 2.0 (MPL 2.0)](./third_party_licenses/MPL-2.0.txt)

certifi, pytest-rerunfailures, tqdm

---

#### [GNU Lesser General Public License v2.1 (LGPL-2.1)](./third_party_licenses/LGPL-2.1.txt)

PyGithub

---

#### [GNU Lesser General Public License v3.0 (LGPL-3.0)](./third_party_licenses/LGPL-3.0.txt)

python-gitlab

---
