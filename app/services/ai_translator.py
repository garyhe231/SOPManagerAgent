"""
Use Claude to translate raw extracted text into a structured SOP markdown document.
"""
import anthropic

_client = anthropic.Anthropic()

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

    message = _client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
