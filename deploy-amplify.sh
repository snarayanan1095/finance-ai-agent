#!/bin/bash

# AWS Amplify Deployment Script for Finance AI Agent
# This script helps deploy the application to AWS Amplify

set -e

echo "🚀 Deploying Finance AI Agent to AWS Amplify..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if amplify CLI is installed
if ! command -v amplify &> /dev/null; then
    echo "❌ Amplify CLI is not installed. Please install it first:"
    echo "npm install -g @aws-amplify/cli"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Step 1: Initialize Amplify (if not already done)
if [ ! -d ".amplify" ]; then
    echo "📋 Initializing Amplify project..."
    amplify init --app https://github.com/your-username/finance-ai-agent
else
    echo "✅ Amplify project already initialized"
fi

# Step 2: Add hosting
echo "🌐 Adding hosting..."
amplify add hosting

# Step 3: Deploy backend services (Lambda + DynamoDB)
echo "🔧 Deploying backend services..."

# Create Lambda function
aws lambda create-function \
    --function-name finance-email-fetcher \
    --runtime python3.12 \
    --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://fetcher/lambda_function.py \
    --timeout 60 \
    --memory-size 512 \
    --environment Variables='{
        "EMAIL_HOST":"imap.gmail.com",
        "EMAIL_USER":"your-email@gmail.com",
        "EMAIL_PASSWORD":"your-app-password",
        "DYNAMODB_TABLE":"transactions",
        "OPENAI_API_KEY":"your-openai-key"
    }' || echo "⚠️  Lambda function may already exist"

# Create DynamoDB table
aws dynamodb create-table \
    --table-name transactions \
    --attribute-definitions AttributeName=txn_id,AttributeType=S \
    --key-schema AttributeName=txn_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST || echo "⚠️  DynamoDB table may already exist"

# Step 4: Push to Amplify
echo "📤 Pushing to Amplify..."
amplify push

echo "✅ Deployment completed!"
echo "🌍 Your app should be available at: https://main.$(aws sts get-caller-identity --query Account --output text).amplifyapp.com"
echo ""
echo "📝 Next steps:"
echo "1. Configure environment variables in Amplify Console"
echo "2. Set up EventBridge rule for Lambda scheduling"
echo "3. Test the application" 