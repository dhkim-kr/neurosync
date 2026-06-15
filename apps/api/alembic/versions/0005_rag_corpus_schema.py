"""rag corpus + ontology schema (pgvector).

PRD §5.2 "Embedding (pgvector) deferred to Phase 2 RAG migration" (see 0002).
This migration adds the `rag` schema: psychiatry case cards, QA knowledge,
disease/symptom ontology, and per-session personalization memory.

- Requires the `pgvector/pgvector` Postgres image (CREATE EXTENSION vector).
- Embeddings are Upstage solar 4096-dim. No ANN index (>2000 dims → exact scan;
  corpus is a few thousand rows, full-scan is fine).
- session_insights is a 1:1 extension of public.sessions (AI results persisted
  by Platform — docs/ai §3.3); it references public.sessions / public.users.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS rag")

    # 1) case_card — 심리상담 사례 카드 (남의 유사사례). situation 임베딩.
    op.execute(
        """
        CREATE TABLE rag.case_card (
          card_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          person_id       TEXT NOT NULL,
          session_no      INT,
          class           TEXT NOT NULL,
          age             INT,
          gender          TEXT,
          sev_depression  INT,
          sev_anxiety     INT,
          sev_addiction   INT,
          total_time      INT,
          silence         REAL,
          flag_suicidal   BOOLEAN DEFAULT FALSE,
          flags           JSONB,
          situation       TEXT NOT NULL,
          intervention    TEXT,
          summary_full    TEXT,
          source_ref      TEXT NOT NULL UNIQUE,
          embedding       vector(4096),
          embedding_model TEXT
        )
        """
    )
    op.execute("CREATE INDEX idx_card_class    ON rag.case_card(class)")
    op.execute("CREATE INDEX idx_card_suicidal ON rag.case_card(flag_suicidal)")
    op.execute("CREATE INDEX idx_card_flags    ON rag.case_card USING gin(flags)")

    # 2) qa — 정신과 QA (지식 근거). question 임베딩.
    op.execute(
        """
        CREATE TABLE rag.qa (
          qa_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          specialty       TEXT NOT NULL,
          question        TEXT NOT NULL,
          answer          TEXT NOT NULL,
          source_ref      TEXT UNIQUE,
          embedding       vector(4096),
          embedding_model TEXT
        )
        """
    )

    # 3) disease — 질병 마스터 (Ada 26).
    op.execute(
        """
        CREATE TABLE rag.disease (
          disease_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          slug        TEXT UNIQUE NOT NULL,
          name        TEXT NOT NULL,
          name_ko     TEXT NOT NULL,
          kcd_code    TEXT,
          category    TEXT,
          description TEXT,
          source      TEXT DEFAULT 'ada'
        )
        """
    )

    # 4) symptom — 증상 마스터 (canonical flag + Ada synonym).
    op.execute(
        """
        CREATE TABLE rag.symptom (
          symptom_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          name            TEXT UNIQUE NOT NULL,
          name_ko         TEXT,
          bucket          TEXT,
          synonyms        JSONB,
          source          TEXT,
          embedding       vector(4096),
          embedding_model TEXT
        )
        """
    )

    # 5) disease_symptom — 질병↔증상 (m:n 존재 그래프, weight 없음).
    op.execute(
        """
        CREATE TABLE rag.disease_symptom (
          disease_id BIGINT NOT NULL REFERENCES rag.disease(disease_id) ON DELETE CASCADE,
          symptom_id BIGINT NOT NULL REFERENCES rag.symptom(symptom_id) ON DELETE CASCADE,
          source     TEXT NOT NULL,
          PRIMARY KEY (disease_id, symptom_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_ds_symptom ON rag.disease_symptom(symptom_id)")

    # 6) session_insights — 개인 메모리 카드 (PHI). public.sessions 1:1 확장.
    op.execute(
        """
        CREATE TABLE rag.session_insights (
          session_id             UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
          patient_id             UUID NOT NULL REFERENCES users(id),
          class                  TEXT,
          flags                  JSONB,
          flag_suicidal          BOOLEAN DEFAULT FALSE,
          flag_source            TEXT DEFAULT 'agent',
          phq9_score             INT,
          gad7_score             INT,
          situation_encrypted    BYTEA,
          intervention_encrypted BYTEA,
          embedding              vector(4096),
          embedding_model        TEXT,
          generated_at           TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_si_patient ON rag.session_insights(patient_id, generated_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_si_suicidal ON rag.session_insights(patient_id) WHERE flag_suicidal"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS rag CASCADE")
    # vector extension left in place (may be used elsewhere).
