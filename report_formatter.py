import os
from typing import Dict, Any
from datetime import datetime

def format_report(analysis_data: Dict[str, Any], input_filename: str) -> str:
    """
    Formats the analysis data into a structured Markdown report, mimicking a human-written style.

    Args:
        analysis_data: The dictionary containing analysis results from the engine.
        input_filename: The name of the source log file.

    Returns:
        A string containing the formatted markdown report.
    """
    report_parts = []
    MIN_LOG_LENGTH = 20  # 의미 있는 로그로 판단하기 위한 최소 길이

    # Header
    report_parts.append(f"# 오류 분석 보고서: {os.path.basename(input_filename)}")
    report_parts.append(f"> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Section 1: 개요
    report_parts.append("## 1. 개요")
    report_parts.append(f"{analysis_data.get('summary', '분석 정보를 가져올 수 없습니다.')}\n")

    # Section 2: 추정 원인 분석
    report_parts.append("## 2. 추정 원인 분석")
    root_causes = analysis_data.get('root_causes', [])
    if root_causes:
        if len(root_causes) == 1:
            report_parts.append("가장 유력한 원인은 다음과 같습니다:")
        else:
            report_parts.append("분석 결과, 다음과 같은 주요 원인이 추정됩니다:")
        for cause in root_causes:
            report_parts.append(f"- {cause}")
    else:
        report_parts.append("현재까지 수집된 정보로는 명확한 원인을 특정하기 어렵습니다.")
    report_parts.append("\n")

    # Section 3: 근거 로그
    report_parts.append("## 3. 근거 로그")
    evidence_logs = analysis_data.get('evidence', [])
    # 의미 있는(충분히 긴) 로그만 필터링
    meaningful_logs = [log for log in evidence_logs if log and len(log.strip()) > MIN_LOG_LENGTH]
    
    if meaningful_logs:
        report_parts.append("오류의 직접적인 원인으로 판단되는 주요 로그는 다음과 같습니다.")
        for ev in meaningful_logs:
            report_parts.append(f"```log\n{ev.strip()}\n```")
    else:
        report_parts.append("분석에 유의미한 근거 로그를 발견하지 못했습니다.")
    report_parts.append("\n")

    # Section 4: 영향 범위
    report_parts.append("## 4. 영향 범위")
    report_parts.append(f"{analysis_data.get('impact_scope', '분석 정보를 가져올 수 없습니다.')}\n")

    # Section 5: 권장 조치 방안
    report_parts.append("## 5. 권장 조치 방안")
    actions = analysis_data.get('recommended_actions', [])
    if actions:
        if len(actions) == 1:
            report_parts.append("가장 시급하게 다음 조치를 권장합니다:")
        else:
            report_parts.append("문제 해결을 위해 다음 단계별 조치를 권장합니다:")
        for i, action in enumerate(actions, 1):
            report_parts.append(f"{i}. {action}")
    else:
        report_parts.append("자동으로 제안할 수 있는 조치 방안이 없습니다. 담당자의 추가 분석이 필요합니다.")
    report_parts.append("\n")

    # Section 6: 재발 방지 대책
    report_parts.append("## 6. 재발 방지 대책")
    report_parts.append("- `TODO: 담당자 회의 후 논의하여 작성`")

    return "\n".join(report_parts)
