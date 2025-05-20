#!/usr/bin/env bash
set -euo pipefail

# Optional: Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running unit tests...${NC}"
./dev/test/unit.sh

echo -e "${GREEN}Running integration tests...${NC}"
./dev/test/integration.sh

echo -e "${GREEN}Handling test artifacts...${NC}"
./dev/test/artifacts.sh

echo -e "${GREEN}All tests completed successfully!${NC}"
