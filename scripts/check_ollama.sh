#!/bin/bash
# Check and start Ollama service

if pgrep -x "ollama" > /dev/null; then
    echo "✓ Ollama service is already running"
    exit 0
fi

echo "  Starting: ollama serve"
echo "  ⏳  Waiting for Ollama to start..."
ollama serve > /tmp/ollama.log 2>&1 &

# Wait up to 8 seconds for service to start
for i in 1 2 3 4 5 6 7 8; do
    if pgrep -x "ollama" > /dev/null; then
        echo "  ✓ Ollama service started"
        exit 0
    fi
    sleep 1
done

# If we get here, Ollama failed to start
echo ""
echo "❌ Failed to start Ollama service."
echo "Try starting manually in another terminal:"
echo "  ollama serve"
exit 1
