[db_connection_error_report.md](https://github.com/user-attachments/files/24230329/db_connection_error_report.md)
※ 본 문서는 자동 생성된 초기 분석 초안입니다.

# DB 연결 장애 분석 보고서

---

### 1. 개요

| 항목 | 내용 |
| --- | --- |
| 보고서 ID | `INC-20230817-001` |
| 작성일 | 2023년 08월 17일 |
| 작성자 | OOO (SRE Team) |
| 장애 발생 일시 | 2023년 08월 17일 14:30 (KST) |
| 장애 복구 일시 | 2023년 08월 17일 15:15 (KST) |
| 총 장애 시간 | 45분 |
| 영향 받은 서비스 | 사용자 API (`user-api`), 주문 API (`order-api`) |

### 2. 장애 현상

- 14:30 경부터 `user-api` 및 `order-api`의 5xx 에러 응답률이 80% 이상으로 급증함.
- API Gateway에서 다수의 `504 Gateway Timeout` 에러가 관측됨.
- Application 로그에서 `HikariPool-1 - Connection is not available, request timed out after 30000ms` 예외가 다수 발생하며, DB Connection Pool 고갈이 확인됨.
- 사용자 관점에서는 서비스 접속 시 간헐적인 로딩 지연 및 "서버 오류" 페이지가 노출됨.

### 3. 장애 타임라인

| 시간 (KST) | 내용 |
| --- | --- |
| 14:30 | 모니터링 시스템(Datadog)에서 API Latency 및 Error Rate 임계치 초과 알림 발생. |
| 14:32 | 담당 엔지니어가 장애 상황 인지 및 초기 분석 착수. |
| 14:35 | APM 및 로그 분석을 통해 특정 애플리케이션 인스턴스들에서 DB Connection Timeout 확인. |
| 14:40 | DB Connection Pool 현황 확인 결과, Active Connection 수가 Max Pool Size(20)에 도달하여 대기(pending) 스레드가 급증한 상태임을 파악. |
| 14:45 | 긴급 조치로 `user-api` 인스턴스 그룹에 대한 롤링 재시작을 수행했으나, 재시작 직후 다시 커넥션 풀이 고갈되며 현상 재현. |
| 15:00 | 원인 분석 중, 특정 슬로우 쿼리(`SELECT ... FROM user_activities ...`)가 DB 커넥션을 장시간 점유하고 있음을 발견.<br>**(담당자 주석: APM 트레이스에서 해당 쿼리의 P99 Latency가 15초 이상인 것을 직접 확인함)** |
| 15:10 | 근본 원인 해결에 시간이 소요될 것으로 판단, 2차 긴급 조치로 `user-api`, `order-api`의 DB Connection Pool Max Size를 20에서 50으로 상향 조정. |
| 15:15 | 커넥션 풀 상향 조정 후 API 에러율이 정상 수준으로 회복되고 서비스 안정화 확인. |
| 16:00 | 장애 상황 공식 종료 및 사후 분석 보고서 작성 시작. |

### 4. 원인 분석

1.  **직접 원인: DB Connection Pool 고갈**
    - `user-api`와 `order-api`의 데이터베이스 커넥션 풀(HikariCP)이 모두 소진되어 새로운 DB 연결 요청을 처리하지 못함.

2.  **근본 원인: 신규 배포된 기능의 비효율적인 쿼리 및 트래픽 증가**
    - **(Slow Query)**: 금일 11:00에 배포된 '사용자 활동 내역 조회' 기능에 포함된 특정 쿼리가 적절한 인덱스를 사용하지 않아, 일부 다량의 활동 기록을 가진 사용자의 요청 처리 시 과도한 실행 시간을 소요함. <br>**(분석팀 주석: `user_activities` 테이블의 `created_at` 컬럼에 인덱스가 누락되어 Full Table Scan이 발생했음을 실행 계획(Explain) 분석을 통해 확인함.)**
    - **(Traffic Spike)**: 14:25부터 시작된 마케팅 이벤트로 인해 평소 대비 약 300%의 트래픽이 유입됨.
    - 위 두 가지 요인이 복합적으로 작용하여, 슬로우 쿼리가 평소보다 훨씬 많은 수의 DB 커넥션을 장시간 점유하게 되었고, 결국 전체 커넥션 풀을 고갈시키는 결과를 초래함.

### 5. 조치 내용

- **긴급 조치**: 서비스 즉시 복구를 위해 운영 중인 모든 `user-api` 및 `order-api` 인스턴스의 Max Pool Size 설정을 20에서 50으로 실시간 변경 적용함. (Configuration as Code를 통한 동적 변경)

### 6. 재발 방지 대책

| 구분 | 내용 | 담당자/팀 | 기한 |
| --- | --- | --- | --- |
| **단기** | **[완료]** 문제 쿼리(`user_activities` 테이블 조회)에 대한 인덱스 추가 및 쿼리 최적화 후 긴급 패치 배포 | 백엔드팀 | 즉시 |
| **단기** | **[진행]** 애플리케이션 레벨에서 모든 DB 쿼리에 대한 최대 실행 시간(Query Timeout) 설정 적용 | 백엔드팀 | YYYY-MM-DD |
| **중장기** | **[계획]** 신규 쿼리 배포 전, 프로덕션 데이터의 통계 기반 성능 테스트(부하 테스트, 인덱스 실행 계획 분석) 의무화 프로세스 수립 | SRE팀, 백엔드팀 | YYYY-MM-DD |
| **중장기**| **[계획]** 전반적인 서비스의 Connection Pool 및 Timeout 설정값에 대한 재산정 및 표준 가이드라인 수립<br>**(아키텍트 주석: 이번 장애를 계기로, 트래픽 특성에 따른 동적 풀 사이즈 조정(Dynamic Pool Sizing) 도입 검토 필요)** | SRE팀 | YYYY-MM-DD |
