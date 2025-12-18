import os
import json
from typing import Dict, List, Any

# Note: This tool requires the 'openai' and 'python-dotenv' packages.
# Install them with: pip install openai python-dotenv

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    IS_OPENAI_AVAILABLE = True
except ImportError:
    IS_OPENAI_AVAILABLE = False


def _create_llm_client():
    """Initializes and returns the OpenAI client, raising errors on failure."""
    if not IS_OPENAI_AVAILABLE:
        raise ImportError("openai and python-dotenv packages are required for LLM analysis. Please run 'pip install openai python-dotenv'")
    
    load_dotenv()  # Loads variables from .env file if it exists
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set. LLM analysis cannot proceed.")
    return OpenAI(api_key=api_key)

# Initialize the client as a module-level singleton.
# This code runs once upon module import.
CLIENT = _create_llm_client() if IS_OPENAI_AVAILABLE else None

def load_prompt(prompt_name: str) -> str:
    """Loads a prompt from the prompts directory."""
    # Assumes the script is run from the project's root directory
    prompt_path = os.path.join('prompts', f'{prompt_name}.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found at {prompt_path}. Make sure you are running the script from the 'error-report-generator' directory.")

# --- Analysis Guardrails and Configuration ---
# To ensure predictable cost and performance, we define strict limits.

# Maximum log length in characters. Logs exceeding this will be rejected.
MAX_LOG_LENGTH_CHARS = 100000

# Threshold to decide whether to generate a pre-summary for long logs.
# This helps manage token count and reduces cost for subsequent LLM calls.
LOG_LENGTH_THRESHOLD = 8000

# The analysis process is designed with a fixed number of LLM calls (max 5: 1 pre-summary + 4 analysis steps)
# to prevent cost overruns. This constant documents the design constraint.
MAX_LLM_CALLS_PER_ANALYSIS = 5

def call_llm(client, system_prompt: str, user_prompt: str, is_json: bool = False):
    """Generic function to call the LLM API."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response_format = {"type": "json_object"} if is_json else {"type": "text"}
    
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        response_format=response_format,
        temperature=0.2
    )
    return response.choices[0].message.content

def analyze_log(log_text: str) -> Dict[str, Any]:
    """
    Analyzes log text using a multi-prompt chaining approach.
    For long logs, it first creates a pre-summary to use in subsequent steps,
    optimizing for cost and performance.
    """
    # Guardrail: Check if log text exceeds the maximum allowed length before any processing.
    if len(log_text) > MAX_LOG_LENGTH_CHARS:
        error_message = f"로그 길이가 최대 제한({MAX_LOG_LENGTH_CHARS}자)을 초과하여 분석을 진행할 수 없습니다. (현재 길이: {len(log_text)}자)"
        return {
            "summary": error_message,
            "root_causes": ["분석 거부"],
            "evidence": ["분석 거부"],
            "impact_scope": "분석 거부",
            "recommended_actions": ["로그 길이를 줄여 다시 시도하십시오."]
        }

    if not CLIENT:
        raise RuntimeError("LLM client is not initialized. Check OpenAI key and dependencies.")

    analysis_result = {}
    log_context = log_text

    # Pre-summary for long logs to reduce token usage in subsequent calls
    if len(log_text) > LOG_LENGTH_THRESHOLD:
        try:
            print(f"Log text is long ({len(log_text)} chars). Generating pre-summary...")
            pre_summary_prompt = load_prompt('pre_summary').replace('[LOG_CONTEXT]', log_text)
            log_context = call_llm(CLIENT, "You are an expert log analyst that summarizes key information.", pre_summary_prompt)
        except Exception as e:
            # If pre-summary fails, we cannot proceed with analysis.
            error_message = f"선행 요약(Pre-summary) 단계에서 오류 발생: {e}"
            return {
                "summary": error_message,
                "root_causes": ["선행 단계 실패로 분석 불가"],
                "evidence": ["선행 단계 실패로 분석 불가"],
                "impact_scope": "선행 단계 실패로 분석 불가",
                "recommended_actions": ["선행 단계 실패로 분석 불가"]
            }

    # The rest of the analysis process consists of a fixed number of steps,
    # adhering to the MAX_LLM_CALLS_PER_ANALYSIS constraint.

    # 1. Summary
    try:
        summary_prompt = load_prompt('summary').replace('[LOG_CONTEXT]', log_context)
        analysis_result['summary'] = call_llm(CLIENT, "You are an expert log analyst.", summary_prompt)
    except Exception as e:
        analysis_result['summary'] = f"오류: [요약] 단계 실패 - {e}"

    # 2. Root Cause & Evidence (structured JSON output)
    try:
        rc_prompt = load_prompt('root_cause').replace('[LOG_CONTEXT]', log_context)
        rc_response_str = call_llm(CLIENT, "You are a root cause analysis expert. Respond in the requested JSON format.", rc_prompt, is_json=True)
        rc_data = json.loads(rc_response_str)
        analysis_result['root_causes'] = rc_data.get('root_causes', ["정보 부족"])
        analysis_result['evidence'] = rc_data.get('evidence', ["정보 부족"])
    except Exception as e:
        analysis_result['root_causes'] = [f"오류: [원인 분석] 단계 실패 - {e}"]
        analysis_result['evidence'] = ["오류로 인해 증거를 추출할 수 없습니다."]

    # 3. Impact Scope
    try:
        impact_prompt = load_prompt('impact_scope').replace('[LOG_CONTEXT]', log_context)
        analysis_result['impact_scope'] = call_llm(CLIENT, "You are a system architect assessing business and technical impact.", impact_prompt)
    except Exception as e:
        analysis_result['impact_scope'] = f"오류: [영향 범위] 단계 실패 - {e}"

    # 4. Recommended Actions (structured JSON output)
    try:
        actions_prompt = load_prompt('actions').replace('[LOG_CONTEXT]', log_context)
        actions_response_str = call_llm(CLIENT, "You are a senior engineer providing actionable recommendations. Respond in the requested JSON format.", actions_prompt, is_json=True)
        actions_data = json.loads(actions_response_str)
        analysis_result['recommended_actions'] = actions_data.get('recommended_actions', ["정보 부족"])
    except Exception as e:
        analysis_result['recommended_actions'] = [f"오류: [조치 추천] 단계 실패 - {e}"]
    
    return analysis_result
