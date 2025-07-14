#!/bin/bash

# AWS App Runner Deployment Script for Finance AI Agent
# This script deploys the Streamlit app to AWS App Runner

set -e

echo "🚀 Deploying Finance AI Agent to AWS App Runner..."

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install it first."
    exit 1
fi

# Configuration
AWS_REGION=${AWS_REGION:-"us-west-2"}
SERVICE_NAME="finance-ai-agent"
ECR_REPO_NAME="finance-ai-agent"

echo "✅ Prerequisites check passed"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $AWS_ACCOUNT_ID"

# Step 1: Create ECR repository
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || echo "✅ ECR repository already exists"

# Step 2: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 3: Build Docker image
echo "🔨 Building Docker image..."
docker build -t $SERVICE_NAME .

# Step 4: Tag and push image
echo "📤 Pushing Docker image to ECR..."
docker tag $SERVICE_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

# Step 5: Create IAM role for App Runner (if it doesn't exist)
echo "🔑 Setting up IAM roles..."
ROLE_NAME="AppRunnerECRAccessRole"

# Create the trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json 2>/dev/null || echo "✅ IAM role already exists"

# Attach the required policies
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess 2>/dev/null || echo "✅ Policy already attached"

# Create DynamoDB access policy
cat > dynamodb-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:$AWS_REGION:$AWS_ACCOUNT_ID:table/transactions"
    }
  ]
}
EOF

aws iam put-role-policy --role-name $ROLE_NAME --policy-name DynamoDBAccess --policy-document file://dynamodb-policy.json 2>/dev/null || echo "✅ DynamoDB policy already attached"

# Step 6: Create App Runner service
echo "🌐 Creating App Runner service..."

# Check if service already exists
SERVICE_ARN=$(aws apprunner list-services --region $AWS_REGION --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text)

if [ -z "$SERVICE_ARN" ]; then
    echo "📋 Creating new App Runner service..."
    
    # Create the service
    SERVICE_ARN=$(aws apprunner create-service \
        --service-name $SERVICE_NAME \
        --region $AWS_REGION \
        --source-configuration "{
            \"AuthenticationConfiguration\": {
                \"AccessRoleArn\": \"arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME\"
            },
            \"ImageRepository\": {
                \"ImageIdentifier\": \"$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest\",
                \"ImageRepositoryType\": \"ECR\",
                \"ImageConfiguration\": {
                    \"Port\": \"8501\"
                }
            }
        }" \
        --instance-configuration "{
            \"Cpu\": \"1 vCPU\",
            \"Memory\": \"2 GB\"
        }" \
        --query "Service.ServiceArn" \
        --output text)
    
    echo "✅ App Runner service created: $SERVICE_ARN"
else
    echo "✅ App Runner service already exists: $SERVICE_ARN"
fi

# Step 7: Update service with environment variables
echo "⚙️  Configuring environment variables..."

# Prompt for environment variables
echo "Please provide the following environment variables:"
read -p "Email Host (e.g., imap.gmail.com): " EMAIL_HOST
read -p "Email User: " EMAIL_USER
read -s -p "Email Password: " EMAIL_PASSWORD
echo
read -s -p "OpenAI API Key: " OPENAI_API_KEY
echo

# Update the service with environment variables
aws apprunner update-service \
    --service-arn $SERVICE_ARN \
    --region $AWS_REGION \
    --source-configuration "{
        \"AuthenticationConfiguration\": {
            \"AccessRoleArn\": \"arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME\"
        },
        \"ImageRepository\": {
            \"ImageIdentifier\": \"$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest\",
            \"ImageRepositoryType\": \"ECR\",
            \"ImageConfiguration\": {
                \"Port\": \"8501\",
                \"RuntimeEnvironmentVariables\": {
                    \"DYNAMODB_TABLE\": \"transactions\",
                    \"AWS_REGION\": \"$AWS_REGION\",
                    \"EMAIL_HOST\": \"$EMAIL_HOST\",
                    \"EMAIL_USER\": \"$EMAIL_USER\",
                    \"EMAIL_PASSWORD\": \"$EMAIL_PASSWORD\",
                    \"OPENAI_API_KEY\": \"$OPENAI_API_KEY\"
                }
            }
        }
    }"

# Step 8: Create DynamoDB table (if it doesn't exist)
echo "🗄️  Setting up DynamoDB table..."
aws dynamodb create-table \
    --table-name transactions \
    --region $AWS_REGION \
    --attribute-definitions AttributeName=txn_id,AttributeType=S \
    --key-schema AttributeName=txn_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST 2>/dev/null || echo "✅ DynamoDB table already exists"

# Step 9: Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
aws apprunner wait service-running --service-arn $SERVICE_ARN --region $AWS_REGION

# Get the service URL
SERVICE_URL=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $AWS_REGION --query "Service.ServiceUrl" --output text)

echo "✅ Deployment completed!"
echo "🌍 Your app is available at: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Test the application at: $SERVICE_URL"
echo "2. Set up EventBridge rule for Lambda scheduling (if needed)"
echo "3. Configure CloudWatch monitoring and alerts"
echo "4. Set up CI/CD pipeline for automated deployments"

# Clean up temporary files
rm -f trust-policy.json dynamodb-policy.json

echo "🎉 Deployment script completed successfully!" 