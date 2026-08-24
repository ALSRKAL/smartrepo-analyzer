"""Optional AI-powered code summarization via the OpenAI API.

تلخيص الكود بالذكاء الاصطناعي (اختياري) عبر واجهة OpenAI،
بدعم كلا إصداري المكتبة (>=1.0 والقديمة) مع معالجة آمنة للأخطاء.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# The openai package is entirely optional: analysis works without it.
try:
    import openai  # noqa: N811
    HAS_OPENAI = True
except ImportError:  # pragma: no cover - depends on environment
    openai = None
    HAS_OPENAI = False

SYSTEM_PROMPT = "You are an expert code summarizer. Be concise and technical."
USER_TEMPLATE = (
    "Summarize what this code does in a concise, professional way "
    "(max 10 lines). Focus on purpose, key functions and data flow:\n\n{content}"
)

_WARNED = False


def ai_summarize_code(
    file_path: Path,
    api_key: str,
    model: str = "gpt-4o-mini",
    max_chars: int = 6000,
    base_url: Optional[str] = None,
) -> Optional[str]:
    """Summarize a source file using OpenAI; returns None on any failure.

    يلخص ملفًا برمجيًا باستخدام نموذج OpenAI. يقص المحتوى الطويل إلى
    ``max_chars`` حرفًا لتقليل التكلفة. يعيد None عند أي خطأ بدلًا من
    إيقاف التحليل بالكامل.
    """
    global _WARNED
    if not HAS_OPENAI:
        if not _WARNED:
            print("⚠ openai package not installed — skipping AI summaries (pip install openai)")
            _WARNED = True
        return None

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not content.strip():
        return None
    content = content[:max_chars]

    try:
        if hasattr(openai, "OpenAI"):  # openai >= 1.0 SDK
            client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_TEMPLATE.format(content=content)},
                ],
                max_tokens=300,
                temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip() or None
        # Legacy openai < 1.0 SDK
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEMPLATE.format(content=content)},
            ],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:  # network, auth, quota errors must not stop analysis
        print(f"⚠ AI summarization failed for {file_path.name}: {e}")
        return None
