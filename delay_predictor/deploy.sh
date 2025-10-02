#!/bin/bash

# Production Deployment Script for Delay Predictor App
# This script automates the deployment process

set -e

echo "🚀 Starting Delay Predictor App Deployment..."

# Configuration
APP_NAME="delay_predictor"
SITE_NAME="delay_predictor_site"
BENCH_DIR="/home/frappe/frappe-bench"
APP_DIR="$BENCH_DIR/apps/$APP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    exit 1
fi

# Check if bench is installed
if ! command -v bench &> /dev/null; then
    print_error "Bench is not installed. Please install bench first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    print_error "Please run this script from the app root directory"
    exit 1
fi

print_status "Installing Python dependencies..."
pip install -r requirements.txt

print_status "Installing app in bench..."
bench get-app $APP_NAME .

print_status "Installing app on site..."
bench --site $SITE_NAME install-app $APP_NAME

print_status "Running database migrations..."
bench --site $SITE_NAME migrate

print_status "Building assets..."
bench --site $SITE_NAME build

print_status "Clearing cache..."
bench --site $SITE_NAME clear-cache

print_status "Restarting services..."
bench restart

print_status "Running health check..."
if curl -f http://localhost:8000/api/method/ping; then
    print_status "✅ Deployment successful! App is running on http://localhost:8000"
else
    print_error "❌ Health check failed. Please check the logs."
    exit 1
fi

print_status "🎉 Delay Predictor App deployment completed successfully!"
print_status "📊 Access the app at: http://localhost:8000"
print_status "🔧 Admin credentials: Administrator / admin"
print_status "📝 Check logs at: $BENCH_DIR/logs/"
