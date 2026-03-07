#!/bin/bash
# Message Integrate Agent - Docker Startup Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Building and starting Message Integrate Agent with Docker...${NC}"

# Build and start containers
docker-compose up --build -d

echo -e "${GREEN}Services started!${NC}"
echo ""
echo -e "${YELLOW}Gateway:${NC}      http://localhost:8080"
echo -e "${YELLOW}MCP Server:${NC} http://localhost:8081"
echo -e "${YELLOW}Health Check:${NC} http://localhost:8080/health"
echo ""
echo -e "View logs: docker-compose logs -f"
echo -e "Stop: docker-compose down"
