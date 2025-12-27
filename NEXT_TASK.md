# 🎯 Next Task: Additional Embedding Providers (Gemini, Claude, Groq)

## Quick Summary

LangOrch currently supports **OpenAI** and **Ollama** embedding providers. Your task is to add support for **Google Gemini**, **Claude (Anthropic)**, and **Groq**.

---

## 📋 What's Already Done

✅ **Multi-provider infrastructure complete**:
- Abstract base class (`BaseEmbeddingProvider`)
- Provider factory pattern
- OpenAI provider (fully working)
- Ollama provider (fully working)
- Settings API (`/api/v1/settings/embedding-provider`)
- Frontend settings page with provider dropdown
- HashiCorp Vault for API key storage
- Database schema with `embedding_provider` & `embedding_config` columns

---

## 🎯 Your Task

Implement 3 new embedding providers:

1. **Google Gemini** ✅ (Full support - has embeddings API)
2. **Claude/Anthropic** ⚠️ (Use Voyage AI or mark as unsupported)
3. **Groq** ⚠️ (No embeddings API - graceful unsupported or skip)

---

## 📚 Complete Implementation Guide

**Read this file first**: `docs/development-phases/V0.2.6_ADDITIONAL_PROVIDERS_PROMPT.md`

This file contains:
- ✅ Full API documentation for each provider
- ✅ Code examples and implementation patterns
- ✅ Step-by-step implementation guide
- ✅ Testing instructions
- ✅ Vault integration examples
- ✅ Frontend updates needed

---

## 🔑 Key Files to Understand

### Backend (Reference Implementations):
1. `backend/app/services/embedding_providers/base.py` - Abstract interface
2. `backend/app/services/embedding_providers/openai_provider.py` - Full example
3. `backend/app/services/embedding_providers/ollama_provider.py` - Local provider example
4. `backend/app/services/embedding_providers/factory.py` - Provider instantiation

### Frontend:
5. `frontend/components/settings/embedding-provider-settings.tsx` - UI component
6. `frontend/lib/types.ts` - TypeScript types

---

## 🎯 Priority Focus

**Priority 1: Google Gemini** (Must implement)
- Gemini has a native embeddings API
- Model: `text-embedding-004` (768 dimensions)
- API: `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent`
- Full documentation in prompt file

**Priority 2: Claude** (Graceful handling)
- Anthropic doesn't have native embeddings yet
- Option A: Use Voyage AI (Anthropic's partner)
- Option B: Mark as "Coming Soon" with clear message

**Priority 3: Groq** (Optional)
- Groq doesn't support embeddings
- Either skip or mark as unsupported

---

## ✅ Success Criteria

You're done when:

1. ✅ User can select "Google Gemini" in Settings page
2. ✅ User can enter Gemini API key
3. ✅ "Test Connection" validates API key
4. ✅ Documents upload & process with Gemini embeddings
5. ✅ Search works with Gemini vectors
6. ✅ Claude shows clear status (working or unsupported)
7. ✅ No backend errors
8. ✅ No TypeScript errors

---

## 🚫 Important: What NOT to Do

1. ❌ **Don't create new markdown files** - Update existing `DEVELOPMENT_ROADMAP.md` only
2. ❌ **Don't modify working providers** - OpenAI & Ollama are done, leave them alone
3. ❌ **Don't change database schema** - Already updated
4. ❌ **Don't modify Settings API** - Already working
5. ❌ **Don't create root-level test scripts** - Use `backend/scripts/` or `backend/tests/`

---

## 📦 Deliverables

### New Files:
- `backend/app/services/embedding_providers/gemini_provider.py`
- `backend/app/services/embedding_providers/claude_provider.py` (or stub)
- `backend/app/services/embedding_providers/groq_provider.py` (optional)

### Updated Files:
- `backend/app/services/embedding_providers/factory.py` (add new providers)
- `frontend/lib/types.ts` (add to ProviderType enum)
- `frontend/components/settings/embedding-provider-settings.tsx` (add to dropdown)
- `docs/development-phases/DEVELOPMENT_ROADMAP.md` (mark tasks complete)

---

## 🔐 Vault Integration

API keys stored in Vault:

```bash
# Gemini
tenants/<tenant-id>/embedding-providers/gemini
  ↳ api_key: "YOUR_GEMINI_KEY"

# Claude (Voyage AI)
tenants/<tenant-id>/embedding-providers/claude
  ↳ api_key: "YOUR_VOYAGE_KEY"
```

---

## 📖 Documentation

All detailed instructions are in:
**`docs/development-phases/V0.2.6_ADDITIONAL_PROVIDERS_PROMPT.md`**

This includes:
- API documentation links
- Code examples
- Error handling patterns
- Testing instructions
- Vault commands

---

## 🚀 Getting Started

1. Read `docs/development-phases/V0.2.6_ADDITIONAL_PROVIDERS_PROMPT.md` thoroughly
2. Review existing providers (`openai_provider.py`, `ollama_provider.py`)
3. Implement Gemini provider first (highest priority)
4. Update factory.py to register Gemini
5. Test Gemini end-to-end
6. Handle Claude gracefully (Voyage AI or unsupported message)
7. Update frontend dropdown
8. Update DEVELOPMENT_ROADMAP.md

---

## 💡 Tips

- Follow existing code style exactly
- Use structured logging (`structlog`)
- Implement async/await properly
- Handle errors gracefully (return `None`, don't crash)
- Test connection before saving settings
- Batch processing for performance (where supported)

---

**Priority**: Focus on **Gemini first** (fully supported API). Handle Claude/Groq gracefully if they don't have embeddings endpoints.

**Good luck!** 🚀
