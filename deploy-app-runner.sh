#!/bin/bash

# AWS App Runner Deployment Script for Finance AI Agent
# This script deploys the Streamlit app to AWS App Runner

set -e

echo "🚀 Deploying Finance AI Agent to AWS App Runner..."

# Configuration
REGION="us-west-2"
REPOSITORY_NAME="finance-ai-agent"
SERVICE_NAME="finance-ai-agent"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

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

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_status "Prerequisites check passed"

# Step 1: Create ECR Repository
print_status "Creating ECR repository..."
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION 2>/dev/null || print_warning "Repository already exists"

# Step 2: Get ECR login token
print_status "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Step 3: Build Docker image
print_status "Building Docker image..."
docker build -t $REPOSITORY_NAME .

# Step 4: Tag image for ECR
print_status "Tagging image for ECR..."
docker tag $REPOSITORY_NAME:latest $ECR_URI/$REPOSITORY_NAME:latest

# Step 5: Push image to ECR
print_status "Pushing image to ECR..."
docker push $ECR_URI/$REPOSITORY_NAME:latest

# Step 6: Create App Runner service
print_status "Creating App Runner service..."

# Create service configuration JSON
cat > app-runner-config.json << EOF
{
    "ServiceName": "$SERVICE_NAME",
    "SourceConfiguration": {
        "ImageRepository": {
            "ImageIdentifier": "$ECR_URI/$REPOSITORY_NAME:latest",
            "ImageConfiguration": {
                "Port": "8501",
                "RuntimeEnvironmentVariables": {
                    "EMAIL_HOST": "imap.gmail.com",
                    "EMAIL_USER": "YOUR_EMAIL@gmail.com",
                    "EMAIL_PASSWORD": "YOUR_APP_PASSWORD",
                    "DYNAMODB_TABLE": "transactions",
                    "OPENAI_API_KEY": "YOUR_OPENAI_KEY"
                }
            }
        },
        "AutoDeploymentsEnabled": true
    },
    "InstanceConfiguration": {
        "Cpu": "1 vCPU",
        "Memory": "2 GB"
    }
}
EOF

# Create the App Runner service
aws apprunner create-service \
    --cli-input-json file://app-runner-config.json \
    --region $REGION

print_status "App Runner service creation initiated..."

# Step 7: Wait for service to be ready
print_status "Waiting for service to be ready..."
SERVICE_ARN=$(aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text)

if [ -z "$SERVICE_ARN" ]; then
    print_error "Could not find service ARN"
    exit 1
fi

echo "Service ARN: $SERVICE_ARN"

# Wait for service to be ready
while true; do
    STATUS=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION --query "Service.Status" --output text)
    print_status "Service status: $STATUS"
    
    if [ "$STATUS" = "RUNNING" ]; then
        break
    elif [ "$STATUS" = "FAILED" ]; then
        print_error "Service creation failed"
        exit 1
    fi
    
    sleep 30
done

# Step 8: Get service URL
SERVICE_URL=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION --query "Service.ServiceUrl" --output text)

print_status "✅ Deployment completed successfully!"
echo ""
echo "🌍 Your app is available at: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Update environment variables in App Runner console"
echo "2. Set up DynamoDB table"
echo "3. Create Lambda function for email processing"
echo "4. Set up EventBridge rule for daily execution"
echo ""
echo "🔧 To update the service later:"
echo "docker build -t $REPOSITORY_NAME ."
echo "docker tag $REPOSITORY_NAME:latest $ECR_URI/$REPOSITORY_NAME:latest"
echo "docker push $ECR_URI/$REPOSITORY_NAME:latest"
echo ""
echo "📊 To monitor your service:"
echo "aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION"

# Clean up
rm -f app-runner-config.json 