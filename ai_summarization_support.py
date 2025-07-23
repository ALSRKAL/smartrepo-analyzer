from pathlib import Path
from typing import Optional
import openai

def ai_summarize_code(file_path: Path, api_key: str, model: str = 'gpt-3.5-turbo') -> Optional[str]:
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a code summarizer.'},
            {'role': 'user', 'content': f'Summarize this code in a concise, professional way (max 10 lines):\n{content}'}
        ]
    )
    return response['choices'][0]['message']['content'] 