# RAG 통합 업데이트 일지

- **브랜치**: `feat/rag-db`
- **날짜**: 2026-06-15
- **개요**: 정신과 RAG 검색 레이어를 추가. apps/api가 pgvector로 사례·지식·온톨로지를
  검색해 `grounding`을 만들고, ai-server가 그걸 프롬프트(정신과 EMR)로 주입한다.
- **접점(인터페이스)**: `ChatRequest.grounding` (shared-contracts 단일 소스).
- **데이터 흐름**:
  `apps/api(입력+RAG) → ChatRequest{messages, grounding} → ai-server(프롬프트+LLM)`
  AI는 DB 미접근 — grounding은 입력으로만 받음.

---

## 추가된 파일

### packages/shared-contracts (인터페이스)
| 파일 | 역할 |
|---|---|
| (수정) `contracts/chat.py` | 아래 '수정' 참조 |

### apps/api — RAG 엔진 (Platform / DB 소유)
| 파일 | 역할 |
|---|---|
| `alembic/versions/0005_rag_corpus_schema.py` | **rag 스키마 마이그레이션** — case_card·qa·disease·symptom·disease_symptom·session_insights + pgvector `vector(4096)`. (0002가 예고한 "Phase 2 RAG migration") |
| `src/rag/retrieval.py` | **런타임 검색(async)** — 발화 → grounding 4슬롯 생성, `Grounding` 반환. (chat 서비스가 호출) |
| `src/rag/ontology.py` | **온톨로지** — 버킷맵(67) · 증상 마스터(40) · 질병(26) · disease_symptom KG. 데이터·매핑의 단일 소스. |
| `src/rag/embed.py` | **임베딩** — Upstage solar(passage/query 4096). 키 없으면 더미. |
| `src/rag/__init__.py` | 패키지 진입(역할 설명) |
| `src/rag/tooling/load_ontology.py` | (오프라인) disease/symptom/disease_symptom 적재 — 데이터셋 불필요 |
| `src/rag/tooling/load_case_cards.py` | (오프라인) 심리상담 사례 적재 — `CASE_DATA_DIR` |
| `src/rag/tooling/load_qa.py` | (오프라인) 정신과 QA 적재 — `QA_DATA_DIR` |
| `src/rag/tooling/embed_corpus.py` | (오프라인) 코퍼스 임베딩 — `UPSTAGE_API_KEY`, 증분(NULL만) |
| `src/rag/tooling/_db.py` | (오프라인) sync psycopg 연결 헬퍼 |
| `src/rag/tooling/__init__.py` | 툴링 실행 순서 안내 |
| `src/rag/README.md` | RAG 엔진 안내(구성·실행·환경변수·TODO) |
| `src/rag/bucket_map.md` | 플래그 67개 4군 분류 근거 |
| `src/rag/unmapped_report.md` | Ada 증상 중 미매핑 35건(Tier-3, 텍스트 위임) |

### apps/ai-server — grounding 소비 (AI 도메인)
| 파일 | 역할 |
|---|---|
| `src/api/chat.py` | **`/ai/chat/respond` 라우터** — ChatRequest 받아 프롬프트 조립. `_call_llm`은 **stub**(LLM 미연결). |
| `src/chat/prompt.py` | **프롬프트 주입** — grounding 4슬롯을 시스템 프롬프트(정신과 EMR)로 렌더(신뢰도 차등). |
| `src/chat/__init__.py` | 패키지 진입(역할 설명) |

### infra (Platform)
| 파일 | 역할 |
|---|---|
| `deploy/k8s/postgres/postgres.yaml` | **pgvector StatefulSet**(+Service·ConfigMap·PVC). 운영 배포용. |

---

## 수정된 파일

| 파일 | 변경 | 이유/역할 |
|---|---|---|
| `packages/shared-contracts/.../contracts/chat.py` | `Grounding` 및 하위모델(case/past/knowledge/followup) 추가, `ChatRequest`에 `grounding` 필드 추가 | **api↔ai-server 접점.** RAG 결과를 실어 보내는 단일 소스. |
| `apps/api/src/services/chat.py` | `_build_grounding()` 추가, `respond()`에서 `retrieve_grounding` 호출해 `ChatRequest.grounding`에 주입 | 발화마다 RAG 검색 → 주입. **best-effort**(검색 실패해도 대화 진행). |
| `apps/api/pyproject.toml` | `openai`, `psycopg[binary]` 의존성 추가 | 임베딩(Upstage 호환) + 오프라인 적재. pgvector 연산은 raw SQL이라 별도 lib 불필요. |
| `apps/ai-server/src/main.py` | `chat_router` 등록 | `/ai/chat/respond` 노출. |
| `infra/deploy/docker-compose.yml` | postgres 이미지 `postgres:16-alpine` → `pgvector/pgvector:pg16` | 일반 postgres면 `vector(4096)` 마이그레이션 실패. **벡터검색 필수.** |

---

## 역할 분담 (경계)

| 영역 | 소유 | 한 일 |
|---|---|---|
| **apps/api + infra** | Platform (DB) | rag 스키마 · RAG 검색 엔진 · grounding 생산 · pgvector 인프라 |
| **shared-contracts** | 공유 | `grounding` 접점 정의 |
| **apps/ai-server** | AI (오케스트레이션/프롬프트) | grounding 소비 · 프롬프트 주입 · (예정) LLM 연결 |

---

## 검증

- 전 파일 `py_compile` 통과.
- `Grounding` Pydantic 모델 인스턴스화 + JSON round-trip 성공(ai_client↔ai-server 경로).
- 마이그레이션 체인 0001→…→0005 선형, 단일 head.

## 남은 작업 (TODO)

1. **LLM 연결** — `apps/ai-server/src/api/chat.py::_call_llm` stub 교체(벤더 미정, docs/ai §5).
2. **`uv lock`** — apps/api 의존성 추가분 반영.
3. **코퍼스 데이터 적재** — 로더 실행(데이터셋 경로 + Upstage 키). 스키마·온톨로지는 키 없이 적재 가능.
4. **intake progress 계산** — `chat_respond`의 `ChatProgress` 현재 stub(ratio=0).
5. **증상 추출 고도화** — `retrieval._detect_symptoms` 키워드 → ai-server 구조화 추출(40 플래그). MedRAG 변별자질 확장 여지.
6. **코퍼스 배포** — 데이터는 이미지에 미포함 → pg_dump seed 아티팩트 또는 seed Job.
