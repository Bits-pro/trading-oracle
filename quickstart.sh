#!/bin/bash

# Trading Oracle Quick Start Script
# This script sets up and runs the trading oracle system

set -e

echo "=================================="
echo "Trading Oracle Quick Start"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓ Logs directory created${NC}"

# Check if Redis is running
echo -e "${YELLOW}Checking Redis...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}✗ Redis is not running!${NC}"
    echo "  Please start Redis with: docker-compose up -d redis"
    echo "  Or install and run Redis: brew install redis && redis-server"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py makemigrations
python manage.py migrate
echo -e "${GREEN}✓ Migrations complete${NC}"

# Check if superuser exists
echo -e "${YELLOW}Checking for superuser...${NC}"
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Creating superuser...${NC}"
    echo "Please create a superuser account:"
    python manage.py createsuperuser
    echo -e "${GREEN}✓ Superuser created${NC}"
else
    echo -e "${GREEN}✓ Superuser already exists${NC}"
fi

# Initialize oracle data
echo -e "${YELLOW}Initializing trading oracle data...${NC}"
python manage.py init_oracle
echo -e "${GREEN}✓ Initialization complete${NC}"

echo ""
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo ""
echo "To start the system, run these commands in separate terminals:"
echo ""
echo "Terminal 1 - Django Server:"
echo "  source venv/bin/activate && python manage.py runserver"
echo ""
echo "Terminal 2 - Celery Worker:"
echo "  source venv/bin/activate && celery -A trading_oracle worker -l info"
echo ""
echo "Terminal 3 - Celery Beat:"
echo "  source venv/bin/activate && celery -A trading_oracle beat -l info"
echo ""
echo "Or use the run.sh script to start all services at once."
echo ""
echo "Access points:"
echo "  Admin: http://localhost:8000/admin/"
echo "  API: http://localhost:8000/api/"
echo "  API Docs: http://localhost:8000/api/"
echo ""
echo "Quick test:"
echo "  python manage.py run_analysis --symbols BTCUSDT --verbose"
