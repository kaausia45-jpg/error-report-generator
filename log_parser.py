import re
from typing import Dict, List, Union

def parse_log_file(file_path: str) -> Dict[str, Union[str, List[str]]]:
    """
    Reads a markdown log file, applies basic masking, and extracts error signals.

    Args:
        file_path: The path to the input .md log file.

    Returns:
        A dictionary containing the masked raw text and a list of found error signals.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except FileNotFoundError:
        return {"raw_text": "", "error_signals": ["File not found"]}
    except Exception as e:
        return {"raw_text": "", "error_signals": [f"Error reading file: {e}"]}

    # Error signal extraction is performed on the original text before masking.
    error_keywords = ['error', 'exception', 'fatal', 'failed', 'traceback', 'critical', 'panic']
    regex = r'\b(' + '|'.join(error_keywords) + r')\b'
    matches = re.findall(regex, raw_text, re.IGNORECASE)
    error_signals = sorted(list(set([match.upper() for match in matches])))

    # Apply basic masking for sensitive data before returning.
    # This is a basic safety measure, not a comprehensive security solution.
    masked_text = raw_text
    # Mask patterns like: api_key="...", secret: '...', token=...
    masked_text = re.sub(
        r'(?i)(api_key|secret|password|token)[\s:="\'`]+([a-zA-Z0-9_\-]{16,})',
        r'\1="<MASKED>"',
        masked_text
    )
    # Mask long, random-looking strings that could be tokens or bearer tokens.
    masked_text = re.sub(
        r'\b[a-zA-Z0-9\-_/+=]{40,}\b',
        '<MASKED_TOKEN>',
        masked_text
    )

    return {
        "raw_text": masked_text, # Return masked text for improved safety.
        "error_signals": error_signals
    }
