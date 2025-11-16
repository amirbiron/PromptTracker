#!/bin/bash

# סקריפט להרצה מקומית של הבוט

echo "🚀 Starting PromptTracker Bot..."
echo ""

# בדיקת Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# בדיקת .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env file with your credentials"
    exit 1
fi

# בדיקת venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# הפעלת venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# התקנת תלויות
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# הרצת הבוט
echo ""
echo "✅ Starting bot..."
echo "Press Ctrl+C to stop"
echo ""
python bot.py
