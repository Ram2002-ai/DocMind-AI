#!/bin/bash

# DocuMind AI Setup Script

echo "🚀 DocuMind AI - Setup Script"
echo "=================================="

# Check if .env file exists
if [ ! -f backend/.env ]; then
    echo "Creating .env file from template..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please update backend/.env with your credentials (GEMINI_API_KEY, JWT_SECRET)"
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if Node is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""
echo "📦 Installing dependencies..."

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Update backend/.env with your GEMINI_API_KEY"
echo "2. Set up PostgreSQL database (or use docker-compose)"
echo "3. Run migrations: alembic upgrade head"
echo "4. Start backend: cd backend && python -m uvicorn app.main:app --reload"
echo "5. Start frontend: cd frontend && npm run dev"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up -d"
echo ""
