import argparse
import os
import sys
from datetime import datetime
import openai  # For handling specific API errors
from log_parser import parse_log_file
from analysis_engine import analyze_log
from report_formatter import format_report

# Exit Codes for automation pipelines
EXIT_CODE_SUCCESS = 0
EXIT_CODE_GENERAL_ERROR = 1
EXIT_CODE_FILE_NOT_FOUND = 2
EXIT_CODE_EMPTY_FILE = 3
EXIT_CODE_AUTH_ERROR = 4
EXIT_CODE_API_ERROR = 5
EXIT_CODE_PARSING_ERROR = 6


def _log_execution_status(status: str, input_file: str, log_file="usage.log"):
    """Appends an execution log entry to the specified log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 로그에는 전체 경로 대신 파일명만 기록하여 가독성 향상
    log_message = f"[{timestamp}] [{status}] Input: {os.path.basename(input_file)}\n"
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except IOError as e:
        # 로그 파일 쓰기 실패 시에도 프로그램이 중단되지 않도록 stderr에만 오류 출력
        print(f"[CRITICAL] Failed to write to log file '{log_file}': {e}", file=sys.stderr)


def main():
    """Main function to orchestrate the report generation pipeline."""
    parser = argparse.ArgumentParser(description="B2B 오류 분석 보고서 자동 생성기")
    parser.add_argument('--input', type=str, required=True, help='입력 로그 파일(.md) 경로')
    parser.add_argument('--output', type=str, help='출력 보고서 파일(.md) 경로. 지정하지 않으면 입력 파일명에 _report.md가 붙습니다.')
    args = parser.parse_args()

    input_path = args.input
    status = "SUCCESS"  # Assume success until an error occurs

    try:
        if not os.path.exists(input_path):
            print(f"[ERROR] 입력 파일을 찾을 수 없습니다: '{input_path}'", file=sys.stderr)
            status = "FAILURE"
            sys.exit(EXIT_CODE_FILE_NOT_FOUND)

        if args.output:
            output_path = args.output
        else:
            base, _ = os.path.splitext(os.path.basename(input_path))
            output_dir = os.path.dirname(input_path) if os.path.dirname(input_path) else '.'
            output_path = os.path.join(output_dir, f"{base}_report.md")

        print(f"[INFO] Step 1/4: 로그 파일 분석 시작 -> {input_path}")
        log_data = parse_log_file(input_path)
        if not log_data['raw_text'].strip():
            print(f"[ERROR] 로그 파일에 분석할 내용이 없습니다: '{input_path}'", file=sys.stderr)
            status = "FAILURE"
            sys.exit(EXIT_CODE_EMPTY_FILE)

        print("[INFO] Step 2/4: LLM을 통해 오류 분석 중... (시간이 소요될 수 있습니다)")
        analysis_result = analyze_log(log_data['raw_text'])
        
        print("[INFO] Step 3/4: 분석 보고서 포맷팅 중...")
        report_content = format_report(analysis_result, input_path)
        
        print(f"[INFO] Step 4/4: 보고서 저장 중 -> {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print("\n[SUCCESS] 보고서 생성이 성공적으로 완료되었습니다.")

    except openai.AuthenticationError as e:
        status = "FAILURE"
        print(f"\n[ERROR] OpenAI 인증 오류가 발생했습니다.", file=sys.stderr)
        print("        환경변수 'OPENAI_API_KEY'가 올바르게 설정되었는지 확인하십시오.", file=sys.stderr)
        print(f"        (원본 오류: {e})", file=sys.stderr)
        sys.exit(EXIT_CODE_AUTH_ERROR)

    except openai.APIError as e:
        status = "FAILURE"
        print(f"\n[ERROR] OpenAI API 호출 중 오류가 발생했습니다.", file=sys.stderr)
        print(f"        (상태 코드: {getattr(e, 'status_code', 'N/A')}, 오류 유형: {getattr(e, 'type', 'N/A')})", file=sys.stderr)
        sys.exit(EXIT_CODE_API_ERROR)
    
    except (ValueError, TypeError) as e:
        status = "FAILURE"
        print(f"\n[ERROR] LLM 응답을 파싱하거나 처리하는 중 오류가 발생했습니다.", file=sys.stderr)
        print("        API 응답 형식이 예상과 다르거나, 후처리 로직에 문제가 있을 수 있습니다.", file=sys.stderr)
        print(f"        (원본 오류: {e})", file=sys.stderr)
        sys.exit(EXIT_CODE_PARSING_ERROR)

    except Exception as e:
        status = "FAILURE"
        print(f"\n[FATAL] 예상치 못한 오류가 발생했습니다.", file=sys.stderr)
        print(f"        (오류 유형: {type(e).__name__}, 내용: {e})", file=sys.stderr)
        sys.exit(EXIT_CODE_GENERAL_ERROR)
    
    finally:
        _log_execution_status(status, input_path)

if __name__ == "__main__":
    main()
