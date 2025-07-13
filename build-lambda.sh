#!/bin/bash

# Build script for Lambda function
# This creates a deployment package with all dependencies

set -e

echo "🔧 Building Lambda deployment package..."

# Create build directory
BUILD_DIR="lambda-build"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

# Copy Lambda function
echo "📁 Copying Lambda function..."
cp fetcher/lambda_function.py $BUILD_DIR/
cp -r extractor $BUILD_DIR/
cp -r shared $BUILD_DIR/

# Create requirements file for Lambda
echo "📦 Creating Lambda requirements..."
cat > $BUILD_DIR/requirements.txt << EOF
boto3>=1.34.0
mail-parser==3.14.0
openai>=1.12.0
python-dotenv>=1.0.1
EOF

# Install dependencies in build directory
echo "📥 Installing dependencies..."
cd $BUILD_DIR
pip install -r requirements.txt -t .

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Create deployment package
echo "📦 Creating deployment package..."
zip -r ../lambda-deployment.zip . -x "*.pyc" "*.pyo" "*.pyd" "__pycache__/*" "*.dist-info/*"

cd ..

echo "✅ Lambda package created: lambda-deployment.zip"
echo "📊 Package size: $(du -h lambda-deployment.zip | cut -f1)" 