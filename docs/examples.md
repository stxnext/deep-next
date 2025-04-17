---
layout: default
title: Advanced Usage Examples
---

# Advanced Usage Examples

This page provides links to practical examples of how to customize and extend DeepNext for specific use cases.

## Available Examples

- [Chain-of-Thought Prompting](./examples/example_chain_of_thoughts.html) - Enhance the Action Plan stage with improved reasoning
- [Project Map Filtering](./examples/example_project_map_filter.html) - Use LLM to filter out irrelevant files and directories
- [Multi-Implementation Patch Selection](./examples/example_multiple_implementations.html) - Improve patch reliability by generating multiple implementations
- [Another Example](./examples/example_another_example.html) - Another example case

## Adding New Examples

To add a new example:

1. Create a markdown file in the `docs/examples/` directory using this naming pattern: `example_your_technique_name.md`
2. Use the template below for your content
3. Add a link to your example on this index page

### Example Template

```markdown
---
layout: default
title: Your Example Title
---

# Your Example Title

Brief description of what this example accomplishes and why it's useful.

## Implementation

Detailed explanation of the technique or modification.

**Location**: `path/to/relevant/file.py`

```python
# Original code or configuration
...

# Modified code or configuration
...
```

## Benefits

1. **Benefit 1**: Explanation
2. **Benefit 2**: Explanation
3. **Benefit 3**: Explanation

## Implementation Notes

- Key consideration 1
- Key consideration 2
- Key consideration 3

[Back to Examples](../examples.html)
```

[Back to Home](./index.html)
