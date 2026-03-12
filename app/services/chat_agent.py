"""
Chatbot that answers questions about an SOP and can propose edits.

The agent returns either:
  {"type": "answer", "text": "..."}
  {"type": "patch",  "text": "...", "markdown": "<full updated markdown>"}

Streaming is used so the UI can display tokens as they arrive.
"""
import json
import re
from typing import Generator, List, Dict

import anthropic

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert SOP assistant embedded in the SOP Manager.
You have access to the full text of a Standard Operating Procedure (SOP).

You can do two things:
1. Answer questions about the SOP clearly and accurately.
2. Make edits to the SOP when the user requests changes.

IMPORTANT OUTPUT FORMAT:
- For answers/explanations: respond with normal prose. Start with ANSWER:
- For edits: respond with PATCH: followed by a one-sentence summary of your changes,
  then on a new line output the full updated SOP markdown wrapped in ```markdown ... ```

Only output a PATCH when the user explicitly asks to change, update, fix, add, remove,
rewrite, or modify the SOP content. For all other messages output ANSWER:.

Always be concise, accurate, and professional.
"""


def _build_messages(history: List[Dict], sop_markdown: str, user_message: str) -> List[Dict]:
    context_msg = f"""Here is the current SOP content:\n\n```markdown\n{sop_markdown}\n```\n\nUser message: {user_message}"""
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
    Yields Server-Sent Event strings. Each chunk is:
      data: {"delta": "..."}\n\n
    Final chunk when a patch is detected:
      data: {"done": true, "type": "patch"|"answer", "markdown": "..."}\n\n
    """
    messages = _build_messages(history, sop_markdown, user_message)

    full_text = ""
    with _client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            yield f"data: {json.dumps({'delta': text})}\n\n"

    # Parse response type
    if full_text.strip().startswith("PATCH:"):
        # Extract markdown block
        md_match = re.search(r"```markdown\s*([\s\S]+?)\s*```", full_text)
        new_markdown = md_match.group(1).strip() if md_match else ""
        # Summary is text between "PATCH:" and the code block
        summary = re.sub(r"PATCH:\s*", "", full_text)
        summary = re.sub(r"```markdown[\s\S]+?```", "", summary).strip()
        yield f"data: {json.dumps({'done': True, 'type': 'patch', 'summary': summary, 'markdown': new_markdown})}\n\n"
    else:
        answer = re.sub(r"^ANSWER:\s*", "", full_text.strip())
        yield f"data: {json.dumps({'done': True, 'type': 'answer', 'text': answer})}\n\n"
