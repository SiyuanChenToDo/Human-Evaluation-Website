#!/bin/bash
# PythonAnywhere deployment setup script
# Run this in the PythonAnywhere Bash console after cloning the repo

echo "=== Human Evaluation System - Setup ==="

# 1. Install dependencies
echo "[1/4] Installing Python packages..."
pip install --user flask markdown pingouin krippendorff numpy pandas

# 2. Make sure data directory exists
echo "[2/4] Setting up directories..."
mkdir -p reports

# 3. Copy report files (upload reports.zip first via PythonAnywhere Files tab)
echo "[3/4] Checking reports..."
if [ -f "reports.zip" ]; then
    unzip -o reports.zip -d reports/
    echo "  Reports extracted"
else
    echo "  WARNING: reports.zip not found!"
    echo "  Upload reports.zip via the Files tab first."
fi

# 4. Initialize database with report data
echo "[4/4] Initializing database..."
python app.py --init

echo ""
echo "=== Setup complete! ==="
echo "Now go to the Web tab in PythonAnywhere and:"
echo "  1. Click 'Add a new web app'"
echo "  2. Choose 'Flask' and Python 3.11"
echo "  3. Set source code path to: /home/\$USER/Human-Evaluation-Website"
echo "  4. Set WSGI file to: /home/\$USER/Human-Evaluation-Website/wsgi.py"
echo "  5. Click reload"
