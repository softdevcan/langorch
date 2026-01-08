# Changelog

All notable changes to LangOrch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-01-08

### Added
- **Document RAG Operations**: Summarize, Ask (Q&A), Transform
- **Background Task Processing**: All LLM operations run in background to avoid timeouts
- **Multi-Provider LLM Support**: Ollama, OpenAI, Anthropic via LiteLLM
- **Multi-Provider Embedding**: OpenAI, Google Gemini, Anthropic Claude, Ollama
- **Dynamic Embedding Dimensions**: Support for different embedding models
- **Smart Summary Caching**: Reuse existing summaries, force regeneration option
- **Tenant-based Configuration**: Per-tenant LLM and embedding provider settings
- **HashiCorp Vault Integration**: Secure API key management
- **Qdrant Vector Database**: Document chunk storage and semantic search
- **Document Upload & Processing**: PDF and DOCX support with chunking
- **Multi-tenancy**: Full tenant isolation for documents and operations
- **User Authentication**: JWT-based auth with role-based access control

### Changed
- Migrated LLM operations (Ask, Transform) from synchronous to asynchronous with polling
- Extended polling timeout to 10 minutes for long-running operations
- Improved error handling and logging across all services

### Fixed
- Transform operation timeout issue (3+ minutes)
- Duplicate LLM operation records in database
- Summary caching mechanism for better performance

## [Unreleased] - v0.4.0

### Planned
- LangGraph integration for multi-agent workflows
- LangSmith observability and monitoring
- Advanced RAG: reranking, hybrid search, multi-query
- Streaming responses (SSE)
- Conversation history and memory
- Agent-based architecture
