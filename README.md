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

- [MIT License](./third_party_licenses/MIT.txt)
- [Apache License 2.0](./third_party_licenses/Apache-2.0.txt)
- [BSD License (BSD-3-Clause)](./third_party_licenses/BSD-3-Clause.txt)
- [Python Software Foundation License](./third_party_licenses/PSF.txt)
- [Mozilla Public License 2.0 (MPL 2.0)](./third_party_licenses/MPL-2.0.txt)
- [GNU Lesser General Public License v2.1 (LGPL-2.1)](./third_party_licenses/LGPL-2.1.txt)
- [GNU Lesser General Public License v3.0 (LGPL-3.0)](./third_party_licenses/LGPL-3.0.txt)
