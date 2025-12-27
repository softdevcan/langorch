# Ollama Setup Guide - LangOrch

## Overview

Ollama artık LangOrch'un docker-compose yapılandırmasına dahil edilmiştir. Bu sayede lokal embedding modelleri kullanabilirsiniz.

## 🚀 Quick Start

### 1. Ollama'yı Docker ile Başlatın

```bash
# Tüm servisleri başlat (Ollama dahil)
docker-compose up -d

# Sadece Ollama'yı başlat
docker-compose up -d ollama

# Ollama loglarını kontrol et
docker-compose logs -f ollama
```

### 2. Embedding Modellerini İndirin

#### Option A: Manuel İndirme (Recommended)

```bash
# Container içine gir
docker exec -it langorch_ollama bash

# Model indir
ollama pull nomic-embed-text        # 768 dims, recommended
ollama pull mxbai-embed-large       # 1024 dims, high quality
ollama pull all-minilm              # 384 dims, fast

# Modelleri listele
ollama list

# Container'dan çık
exit
```

#### Option B: Initialization Script

```bash
# Script'i container içinde çalıştır
docker exec -it langorch_ollama bash /app/init-models.sh
```

Veya Windows PowerShell'de:

```powershell
# Script'i container'a kopyala ve çalıştır
docker cp infrastructure/docker/ollama/init-models.sh langorch_ollama:/tmp/init-models.sh
docker exec -it langorch_ollama bash /tmp/init-models.sh
```

### 3. LangOrch Settings'de Yapılandırın

1. Frontend'i açın: http://localhost:3000
2. Login: `admin@test.com` / `admin123`
3. Settings → Embedding Provider'a gidin
4. **Provider**: Ollama seçin
5. **Model**: `nomic-embed-text` seçin
6. **Ollama URL**: `http://ollama:11434` (Docker network içinde)
   - **Not**: Eğer backend Docker dışındaysa: `http://localhost:11434`
7. "Test Connection" → Başarılı olmalı ✅
8. "Save Settings" → Kaydedin

## 📊 Model Comparison

| Model | Dimensions | Size | Speed | Use Case |
|-------|-----------|------|-------|----------|
| **nomic-embed-text** | 768 | ~274MB | Medium | General purpose (recommended) |
| **mxbai-embed-large** | 1024 | ~669MB | Slower | High quality embeddings |
| **all-minilm** | 384 | ~46MB | Fast | Fast processing, less accuracy |

## 🔍 Testing

### Test Ollama Availability

```bash
# From host
curl http://localhost:11434/api/version

# Expected response:
# {"version":"0.x.x"}
```

### Test Model Availability

```bash
# List models
docker exec langorch_ollama ollama list

# Test embedding generation
curl http://localhost:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "Hello, this is a test"
  }'
```

## 🐛 Troubleshooting

### Issue: Ollama container not starting

```bash
# Check logs
docker-compose logs ollama

# Restart container
docker-compose restart ollama
```

### Issue: Models not downloading

```bash
# Check disk space
docker exec langorch_ollama df -h

# Check network
docker exec langorch_ollama ping -c 3 ollama.ai

# Try manual pull
docker exec -it langorch_ollama ollama pull nomic-embed-text
```

### Issue: Connection refused from backend

**If backend is in Docker:**
- Use `http://ollama:11434` (service name)

**If backend is on host (outside Docker):**
- Use `http://localhost:11434`

**If using WSL:**
- Use `http://host.docker.internal:11434`

### Issue: Model too slow

Try a smaller model:
```bash
docker exec langorch_ollama ollama pull all-minilm
```

Then update Settings to use `all-minilm` model.

## 📝 Configuration

### Environment Variables

Add to `.env` file (optional):

```env
# Ollama Configuration
OLLAMA_HOST=0.0.0.0
OLLAMA_PORT=11434
OLLAMA_MODELS=nomic-embed-text,mxbai-embed-large,all-minilm
```

### Custom Models

İstediğiniz başka Ollama modelini de kullanabilirsiniz:

```bash
# Search for embedding models
docker exec langorch_ollama ollama search embed

# Pull custom model
docker exec langorch_ollama ollama pull <model-name>
```

## 🔄 Switching Between Providers

### From OpenAI to Ollama

1. Go to Settings → Embedding Provider
2. Change provider to **Ollama**
3. Select model: **nomic-embed-text**
4. URL: `http://ollama:11434` (or `http://localhost:11434`)
5. Test Connection
6. Save Settings
7. **Reprocess existing documents** (optional):
   - Go to Documents page
   - Click "Reprocess" on each document
   - Documents will be re-embedded with Ollama

### From Ollama to OpenAI

1. Go to Settings → Embedding Provider
2. Change provider to **OpenAI**
3. Select model: **text-embedding-3-small**
4. Enter API Key
5. Test Connection
6. Save Settings

## 💡 Tips

1. **Performance**: `nomic-embed-text` offers best balance of speed/quality
2. **Cost**: Ollama is 100% free, runs locally
3. **Privacy**: All data stays on your machine
4. **Offline**: Works without internet (after models are downloaded)
5. **GPU**: If you have NVIDIA GPU, Ollama will automatically use it

## 📚 Resources

- [Ollama Official Docs](https://ollama.ai/docs)
- [Ollama Embedding Models](https://ollama.ai/search?c=embedding)
- [LangOrch Documentation](./docs/README.md)

## 🎯 Next Steps

After setup:
1. Upload a test document
2. Verify it's processed with Ollama
3. Try semantic search
4. Compare OpenAI vs Ollama results

---

**Created**: December 27, 2024
**Version**: 0.2.5
**Maintained By**: LangOrch Team
