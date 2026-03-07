#!/bin/bash
# Message Integrate Agent - Stop Script

echo "Stopping Message Integrate Agent..."

# If running with Docker
if [ -f "docker-compose.yml" ]; then
    docker-compose down
    echo "Docker containers stopped."
fi

# If running locally with virtual environment
if [ -d ".venv" ]; then
    echo "Local environment stopped."
fi

echo "Done."
