#!/bin/bash

# LangOrch Development Environment Startup Script
# Version 0.1 - MVP

set -e

echo "🚀 Starting LangOrch Development Environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is running
echo -e "${BLUE}[1/5] Checking PostgreSQL...${NC}"
if psql -U postgres -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL is not running. Please start PostgreSQL first.${NC}"
    exit 1
fi

# Check if database exists
echo -e "${BLUE}[2/5] Checking database...${NC}"
if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw langorch; then
    echo -e "${GREEN}✓ Database 'langorch' exists${NC}"
else
    echo -e "${YELLOW}Creating database 'langorch'...${NC}"
    psql -U postgres -c "CREATE DATABASE langorch;"
    psql -U postgres -c "CREATE USER langorch WITH PASSWORD 'langorch123';"
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE langorch TO langorch;"
    echo -e "${GREEN}✓ Database created${NC}"
fi

# Run migrations
echo -e "${BLUE}[3/5] Running database migrations...${NC}"
cd backend
alembic upgrade head
echo -e "${GREEN}✓ Migrations completed${NC}"

# Seed test data
echo -e "${BLUE}[4/5] Seeding test data...${NC}"
python scripts/seed_test_data.py
echo -e "${GREEN}✓ Test data seeded${NC}"

# Start services
echo -e "${BLUE}[5/5] Starting services...${NC}"
echo ""
echo -e "${GREEN}Backend will start on: http://localhost:8000${NC}"
echo -e "${GREEN}Frontend will start on: http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}Test Credentials:${NC}"
echo -e "  Admin: admin@test.com / admin123"
echo -e "  User:  user@test.com / user123"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Start backend in background
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
