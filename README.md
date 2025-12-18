# B2B 오류 분석 보고서 자동 생성기

## 프로젝트 목적

이 도구는 엔지니어가 복잡한 로그 파일(.md)을 분석하고 표준화된 보고서 초안을 작성하는 데 드는 시간을 획기적으로 줄이기 위해 설계되었습니다. 로그 파일을 입력으로 받아 LLM을 활용하여 오류의 개요, 원인, 영향 범위, 권장 조치 등을 포함한 마크다운 형식의 보고서를 자동으로 생성합니다. 이를 통해 개발팀은 문제 해결에 더 집중할 수 있습니다.

**주의:** 이 도구는 초기 분석을 돕기 위한 보조 수단이며, 생성된 보고서는 초안입니다. 최종적인 원인 분석과 판단은 반드시 담당 엔지니어의 검토를 거쳐야 합니다.

## 이런 팀에 적합합니다

-   잦은 장애 대응과 사후 분석 보고서(Post-mortem) 작성이 필요한 기술 지원 또는 SRE(Site Reliability Engineering) 팀.
-   다양한 서비스에서 발생하는 로그 포맷을 일관된 형식으로 분석하고 인사이트를 얻고자 하는 팀.
-   반복적인 보고서 작성 업무를 자동화하여 핵심 문제 해결에 집중하고 싶은 엔지니어링 조직.

## 도입 방식

-   **Proof of Concept (PoC):** 내부 로그 데이터를 활용하여 제한된 기간 동안 도구의 유효성을 검증할 수 있습니다.
-   **상용 도입:** PoC 결과를 바탕으로 팀의 요구사항에 맞는 라이선스 플랜을 선택하여 정식 도입합니다.
-   **비동기 지원:** 별도의 도입 미팅 없이, 본 문서를 통해 자체적으로 설치 및 테스트가 가능합니다.



## 설치 방법

1.  **저장소 복제**

    ```bash
    git clone <repository-url>
    cd error-report-generator
    ```

2.  **가상 환경 생성 및 활성화 (권장)**

    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate    # Windows
    ```

3.  **의존성 설치**

    ```bash
    pip install -r requirements.txt
    ```

4.  **환경 변수 설정**

    프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 OpenAI API 키를 추가합니다.

    ```
    # .env
    OPENAI_API_KEY="sk-YourSecretApiKey"
    ```


## 보안 및 데이터 처리 주의사항

-   **외부 API 전송:** 이 도구는 분석을 위해 입력된 로그 데이터의 일부 또는 전체를 외부 LLM 서비스(예: OpenAI API)로 전송할 수 있습니다.
-   **민감 정보:** 로그 파일에 개인정보, API 키, 내부 IP 주소 등 민감한 정보가 포함되어 있다면, 외부로 전송하기 전에 반드시 마스킹하거나 제거하는 것을 강력히 권장합니다.





## 실행 예시

프로젝트 루트 디렉토리(`error-report-generator/`)에서 아래 명령어를 실행합니다.

```bash
python generate_report.py --input ./input_logs/sample.md
```

위 명령어는 `input_logs/` 디렉토리 안에 `sample_report.md`라는 결과 파일을 생성합니다.

## 입력 `.md` 예시

**`./input_logs/sample.md`**

```markdown
# Production Server Error Log - 2024-07-28

**Timestamp:** 2024-07-28T14:35:10Z
**Service:** Authentication Service
**Node ID:** prod-auth-7b4f8c6f-abc12

---

14:35:09 [INFO] User 'john.doe' login attempt from 192.168.1.100.
14:35:10 [ERROR] Traceback (most recent call last):
  File "/app/services/auth.py", line 152, in handle_login
    user_profile = db.get_user_profile(user_id)
  File "/app/utils/database.py", line 88, in get_user_profile
    raise DatabaseConnectionError("Failed to connect to primary database replica.")
database.DatabaseConnectionError: Failed to connect to primary database replica.

14:35:11 [WARN] Login failed for user 'john.doe'. Attempting fallback.
14:35:12 [FATAL] Fallback mechanism failed. Service is now in a degraded state.

```



## 출력 `.md` 예시 (요약본)

**`./input_logs/sample_report.md`**

```markdown
# 오류 분석 보고서: sample.md

> 생성일: 2024-07-28 15:00:00

## 1. 개요

2024년 7월 28일 14:35:10Z 경, 인증 서비스(Authentication Service)에서 데이터베이스 연결 오류가 발생했습니다. 이로 인해 사용자 로그인 처리가 실패했으며, 폴백 메커니즘 또한 작동하지 않아 서비스가 저하 상태에 빠졌습니다.

## 2. 추정 원인 분석

-   애플리케이션이 주 데이터베이스 리플리카에 연결하지 못했습니다. 이는 네트워크 문제, DB 부하 또는 잘못된 설정 때문일 수 있습니다.

## 3. 근거 로그

```log
database.DatabaseConnectionError: Failed to connect to primary database replica.
```

## 4. 영향 범위

이 오류로 인해 모든 사용자의 신규 로그인이 불가능하며, 인증이 필요한 모든 서비스 기능이 중단됩니다. 현재 활성 세션은 유지될 수 있으나, 세션 만료 시 사용자는 재로그인할 수 없습니다.

## 5. 권장 조치 방안

1.  (Immediate) 인증 서비스와 주 데이터베이스 간의 네트워크 연결 상태를 확인합니다.
2.  (Immediate) 데이터베이스 서버의 현재 부하 및 로그를 확인하여 과부하 또는 오류 상태인지 점검합니다.
3.  (Long-term) 데이터베이스 연결 재시도 로직 및 서킷 브레이커 패턴을 구현합니다.

## 6. 재발 방지 대책

- `TODO: 담당자 회의 후 논의하여 작성`

```
