#!/bin/bash
# Ollama Model Initialization Script
# This script pulls recommended embedding models for LangOrch

echo "🦙 Initializing Ollama with embedding models..."

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service to start..."
until ollama list >/dev/null 2>&1; do
    echo "   Ollama not ready yet, waiting 2 seconds..."
    sleep 2
done

echo "✅ Ollama service is ready!"

# Pull recommended embedding models
MODELS=(
    "nomic-embed-text:latest"      # 768 dimensions, best general-purpose
    "mxbai-embed-large:latest"     # 1024 dimensions, high quality
    "all-minilm:latest"            # 384 dimensions, fast and lightweight
)

for model in "${MODELS[@]}"; do
    echo ""
    echo "📥 Pulling model: $model"
    ollama pull "$model"

    if [ $? -eq 0 ]; then
        echo "✅ Successfully pulled: $model"
    else
        echo "❌ Failed to pull: $model"
    fi
done

echo ""
echo "🎉 Model initialization complete!"
echo ""
echo "Available models:"
ollama list

echo ""
echo "📝 You can now use these models in LangOrch Settings:"
echo "   - nomic-embed-text (recommended, 768 dims)"
echo "   - mxbai-embed-large (high quality, 1024 dims)"
echo "   - all-minilm (fast, 384 dims)"
