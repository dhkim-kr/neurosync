"""AI chat 도메인 — /ai/chat/respond.

apps/api가 pgvector RAG로 만든 `grounding`(shared-contracts)을 받아
프롬프트(정신과 EMR 주입)로 조립한다. AI는 DB 미접근 — grounding은 입력으로만 온다.
"""
