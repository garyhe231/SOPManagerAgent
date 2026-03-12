"""
Use Claude via AWS Bedrock to translate raw extracted text into a structured SOP markdown document.
"""
import json
import os

import boto3
from botocore.config import Config

_MODEL = (
    os.getenv("ANTHROPIC_DEFAULT_OPUS_MODEL")
    or os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL")
    or "anthropic.claude-opus-4-6"
)
_AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_bedrock = None


def _get_client():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=_AWS_REGION,
            config=Config(read_timeout=120, connect_timeout=10),
        )
    return _bedrock


def _invoke(system: str, user: str, max_tokens: int = 4096) -> str:
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    })
    resp = _get_client().invoke_model(
        modelId=_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


SYSTEM_PROMPT = """You are an expert technical writer specializing in Standard Operating Procedures (SOPs).
Your task is to convert raw text extracted from documents (PDFs, Word docs, spreadsheets, video transcripts)
into a clean, well-structured SOP in Markdown format.

Follow this SOP template structure:

# [SOP Title]

## Purpose
Brief description of what this SOP covers and why it exists.

## Scope
Who this SOP applies to and what processes/systems it covers.

## Responsibilities
Who is responsible for executing and maintaining this SOP.

## Prerequisites
Tools, access, materials, or knowledge required before starting.

## Procedure
Step-by-step instructions using numbered lists. Break complex steps into sub-steps.

## Quality Checks / Verification
How to verify the procedure was completed correctly.

## Troubleshooting
Common issues and their solutions.

## References
Related documents, systems, or resources.

## Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [date] | [author] | Initial version |

Rules:
- Use clear, imperative language ("Click", "Enter", "Navigate to")
- Number all steps sequentially
- Use bullet points for non-sequential items
- Bold important warnings or notes with **Note:** or **Warning:**
- If content is sparse or unclear, make reasonable inferences but mark assumptions with [assumed]
- Preserve all specific details, numbers, system names, and proper nouns from the source
- Output ONLY the markdown, no commentary before or after
"""


def translate_to_sop(raw_text: str, filename: str, title_hint: str = "") -> str:
    prompt = f"""Convert the following content extracted from "{filename}" into a structured SOP.
{f'Suggested title: {title_hint}' if title_hint else ''}

--- SOURCE CONTENT ---
{raw_text[:40000]}
--- END SOURCE CONTENT ---

Generate the complete SOP markdown now:"""

    return _invoke(SYSTEM_PROMPT, prompt, max_tokens=4096)
