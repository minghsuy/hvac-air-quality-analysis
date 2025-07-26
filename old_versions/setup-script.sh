#!/bin/bash
# Setup script for HVAC Air Quality Analysis project

echo "🏠 Setting up HVAC Air Quality Analysis Project..."

# Check if running from project root
if [ ! -f "README.md" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment file
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your credentials:"
    echo "   - AIRTHINGS_CLIENT_ID"
    echo "   - AIRTHINGS_CLIENT_SECRET"
    echo "   - AIRTHINGS_DEVICE_SERIAL (optional)"
    echo ""
fi

# Create directories if they don't exist
echo "📁 Creating directory structure..."
mkdir -p data/{raw,processed,figures}
mkdir -p logs
mkdir -p docs

# Initialize git if not already
if [ ! -d ".git" ]; then
    echo "🐙 Initializing git repository..."
    git init
    git add .gitignore README.md requirements.txt .env.example
    git commit -m "Initial commit - HVAC air quality analysis project"
fi

# Setup pre-commit hook to check for secrets
echo "🔒 Setting up pre-commit hook to prevent secret leaks..."
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook to check for potential secrets

# Check for common secret patterns
if git diff --cached --name-only | xargs grep -E "(client_secret|CLIENT_SECRET|api_key|API_KEY|password|PASSWORD)" 2>/dev/null; then
    echo "❌ Potential secrets detected in commit!"
    echo "Please check your files and use environment variables instead."
    exit 1
fi

# Check if .env is being committed
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ Attempting to commit .env file!"
    echo "This file contains secrets and should not be committed."
    exit 1
fi

exit 0
EOF

chmod +x .git/hooks/pre-commit

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Airthings credentials"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Test data collection: python src/collect_data.py"
echo "4. Run analysis: python src/analyze_data.py"
echo "5. Open Jupyter for interactive analysis: jupyter notebook notebooks/hvac_analysis.ipynb"
echo ""
echo "Remember: Never commit your .env file or any file containing secrets!"
