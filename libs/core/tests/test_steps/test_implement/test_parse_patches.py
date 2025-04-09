import textwrap

import pytest
from deep_next.core.steps.implement.develop_patch import parse_patches

example_modifications_str = textwrap.dedent(
    """
    <modifications>
    # modification 1
    <file>/home/patryk/PROJECTS/deep-next/README.md</file>
    <original>
    ## Getting Started

    To get started with DeepNext, clone the repository and follow the setup
    instructions for each module you are interested in.

    ## Contributing

    We welcome contributions! Please read our contributing guidelines before
    submitting a pull request.
    </original>
    <patched>
    ## Getting Started

    To get started with DeepNext, clone the repository and follow the setup
    instructions for each module you are interested in.

    ### Setup Instructions

    1. **Clone the Repository**:
       ```bash
       git clone https://github.com/yourusername/deep-next.git
       cd deep-next
       ```

    2. **Install Dependencies**:
       Ensure you have Python 3.9 or later installed. Use the following command
       to install dependencies:
       ```bash
       pip install -r requirements.txt
       ```

    3. **Using Makefile**:
       The Makefile contains various commands to set up and manage the project.
       To set up the development environment, run:
       ```bash
       make setup
       ```

    4. **Configuration**:
       Ensure all necessary environment variables are set. Refer to the
       `pyproject.toml` for additional configuration options.

    5. **Run Tests**:
       To ensure everything is set up correctly, run the tests:
       ```bash
       make test
       ```

    ## Contributing

    We welcome contributions! Please read our contributing guidelines before
    submitting a pull request.
    </patched>
    </modifications>
    """
)


@pytest.mark.parametrize(
    "txt",
    [example_modifications_str],
)
def test_extract_code_from_block(txt: str) -> None:
    code_patches = parse_patches(txt)
    assert len(code_patches) == 1
