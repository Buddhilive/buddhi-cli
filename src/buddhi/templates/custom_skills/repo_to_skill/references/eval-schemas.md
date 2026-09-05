# Skill Evaluation Schema Reference

Guidelines for validating generated skills with evaluation prompts and assertions.

## Test Case Format

Evaluation suites test whether an agent loaded with the skill performs correctly compared to a baseline.

```json
{
  "evals": [
    {
      "id": "eval-01-basic-usage",
      "prompt": "How do I run a basic operation using <tool>?",
      "expected_outputs": [
        "<expected command or code pattern>"
      ],
      "assertions": [
        {
          "type": "contains",
          "value": "<keyword-or-flag>"
        }
      ]
    }
  ]
}
```

## Assertion Types

- `contains`: Checks if the agent output contains specific command syntax or code.
- `not_contains`: Ensures deprecated or forbidden patterns are avoided.
- `matches_regex`: Validates pattern structure.
