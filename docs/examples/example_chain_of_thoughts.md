---
layout: default
title: Chain-of-Thought Prompting Example
---


# Enhancing Action Plan with Chain-of-Thought Prompting

The Action Plan stage is critical for creating a structured approach to problem-solving. By modifying the prompt to incorporate Chain-of-Thought (CoT) prompting, we can improve the quality and reasoning of generated plans.

## Example: Implementing Chain-of-Thought Prompting

Chain-of-Thought is a prompting technique that encourages the LLM to break down complex reasoning into intermediate steps, leading to more accurate and detailed solutions.

**Location**: `libs/core/deep_next/core/steps/action_plan/action_plan.py`

```python
# Original prompt section
role = textwrap.dedent(
    """
    You are an expert software engineer tasked with breaking down a software issue \
    into an ordered action plan with explicit dependencies.

    Following steps should be ordered list of high level actionable goals for the developer \
    allowing him to solve the issue and keep the dependencies intact.

    It is required to include reasoning behind the action plan. Focus on input data, \
    analyze trade-offs and provide complete solution. Be concise and professional.

    Relate to input data while creating a solution.
    """
)

# Enhanced prompt with Chain-of-Thought technique
role = textwrap.dedent(
    """
    You are an expert software engineer tasked with breaking down a software issue \
    into an ordered action plan with explicit dependencies.

    First, analyze the problem systematically:
    1. Understand what the issue is requesting and identify key requirements
    2. Examine the provided code context to understand architecture and patterns
    3. Consider potential solutions and evaluate their trade-offs
    4. Identify which files need to be modified and in what order
    5. Think about potential dependencies between changes

    Only after this analysis, create an ordered list of high-level actionable goals for the developer \
    that will solve the issue while maintaining dependencies. Each step should be clear, concise, \
    and directly actionable.

    It is required to include detailed reasoning behind the action plan. Show your step-by-step \
    thought process to arrive at the solution. Analyze trade-offs explicitly and justify why \
    your approach is optimal given the constraints.

    Relate specifically to the provided input data when creating your solution and \
    reference relevant code snippets or project knowledge to support your decisions.
    """
)
```

[Back to Examples](../examples.html)
