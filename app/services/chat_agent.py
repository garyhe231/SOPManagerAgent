"""
Chatbot that answers questions about an SOP and can propose edits.
Uses AWS Bedrock with streaming via invoke_model_with_response_stream.

The agent returns either:
  {"type": "answer", "text": "..."}
  {"type": "patch",  "summary": "...", "markdown": "<full updated markdown>"}
"""
import json
import os
import re
from typing import Dict, Generator, List

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


SYSTEM_PROMPT = """You are an expert SOP assistant embedded in the SOP Manager.
You have access to the full text of a Standard Operating Procedure (SOP).

You can do two things:
1. Answer questions about the SOP clearly and accurately.
2. Make edits to the SOP when the user requests changes.

IMPORTANT OUTPUT FORMAT:
- For answers/explanations: start your response with ANSWER: followed by your explanation.
- For edits: start with PATCH: followed by a one-sentence summary of your changes,
  then on a new line output the full updated SOP markdown wrapped in ```markdown ... ```

Only output a PATCH when the user explicitly asks to change, update, fix, add, remove,
rewrite, or modify the SOP content. For all other messages output ANSWER:.

Always be concise, accurate, and professional.
"""


def _build_messages(history: List[Dict], sop_markdown: str, user_message: str) -> List[Dict]:
    context_msg = f"Here is the current SOP content:\n\n```markdown\n{sop_markdown}\n```\n\nUser message: {user_message}"
    if not history:
        return [{"role": "user", "content": context_msg}]
    msgs = []
    for turn in history:
        msgs.append({"role": turn["role"], "content": turn["content"]})
    msgs.append({"role": "user", "content": context_msg})
    return msgs


def chat_stream(
    sop_markdown: str,
    history: List[Dict],
    user_message: str,
) -> Generator[str, None, None]:
    """
    Yields Server-Sent Event strings:
      data: {"delta": "..."}\n\n       — streaming token
      data: {"done": true, "type": "patch"|"answer", ...}\n\n  — final event
    """
    messages = _build_messages(history, sop_markdown, user_message)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    })

    response = _get_client().invoke_model_with_response_stream(
        modelId=_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    full_text = ""
    for event in response["body"]:
        chunk = event.get("chunk")
        if not chunk:
            continue
        data = json.loads(chunk["bytes"].decode())
        event_type = data.get("type", "")

        if event_type == "content_block_delta":
            delta = data.get("delta", {}).get("text", "")
            if delta:
                full_text += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"

        elif event_type == "message_stop":
            break

    # Parse final response
    if full_text.strip().startswith("PATCH:"):
        md_match = re.search(r"```markdown\s*([\s\S]+?)\s*```", full_text)
        new_markdown = md_match.group(1).strip() if md_match else ""
        summary = re.sub(r"PATCH:\s*", "", full_text)
        summary = re.sub(r"```markdown[\s\S]+?```", "", summary).strip()
        yield f"data: {json.dumps({'done': True, 'type': 'patch', 'summary': summary, 'markdown': new_markdown})}\n\n"
    else:
        answer = re.sub(r"^ANSWER:\s*", "", full_text.strip())
        yield f"data: {json.dumps({'done': True, 'type': 'answer', 'text': answer})}\n\n"
