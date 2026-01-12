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

## [0.4.0] - 2026-01-12

### Added - LangGraph Workflow Orchestration
- **LangGraph StateGraph**: Dynamic workflow orchestration with JSON configuration
- **Chat Interface**: Real-time conversational UI with message history and SSE streaming
- **Human-in-the-Loop (HITL)**: Workflow approval points with interrupt/resume capability
- **PostgresSaver Checkpoints**: State persistence across sessions with automatic resume
- **Workflow Templates**: Pre-built RAG and Simple Chat workflows
- **Multi-Provider Streaming**: Real-time responses from Ollama, OpenAI, Anthropic
- **Session Management**: Conversation tracking with thread-based state isolation
- **Workflow Nodes**: LLM, Retriever, Relevance Grader, Hallucination Checker, HITL
- **SSE Streaming API**: Server-Sent Events for progressive response generation
- **Floating Approval Panel**: Auto-polling UI for pending HITL approvals

### Backend
- 5 new database tables: `workflows`, `workflow_executions`, `conversation_sessions`, `messages`, `hitl_approvals`
- WorkflowExecutionService with execute, stream, and resume methods
- 8 new workflow API endpoints (execute, stream, resume, sessions, messages)
- 4 new HITL API endpoints (list, get, respond, filter)
- CheckpointManager with PostgreSQL connection pooling
- Workflow builder with JSON-to-StateGraph conversion
- Node registry system for dynamic workflow construction

### Frontend
- ChatInterface component with real-time streaming
- Chat page with session list and management
- ApprovalPanel component with auto-polling
- ScrollArea UI component integration
- Workflow templates helper (RAG, Simple Chat)
- Full i18n support (English, Turkish)
- Dark/light mode compatible components
- Zero lint errors, production-ready code

### Changed
- Updated navigation with Chat link
- Enhanced API client with SSE streaming helper
- Extended TypeScript types for v0.4 features

## [Unreleased] - v0.5.0

### Planned
- Multi-agent collaboration and communication
- External tool integration (API calls, web scraping)
- LangSmith observability and monitoring
- Advanced RAG: reranking, hybrid search, multi-query
- Workflow marketplace for sharing templates
