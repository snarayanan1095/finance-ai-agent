# AWS Amplify Deployment Guide for Finance AI Agent

## Overview
Your Finance AI Agent is a Streamlit application that processes email transactions and stores them in DynamoDB. This guide provides two deployment options:

1. **Option A: AWS App Runner** (Recommended for Streamlit apps)
2. **Option B: Static Web App** (Alternative for Amplify)

## Option A: AWS App Runner Deployment (Recommended)

### Prerequisites
1. AWS CLI installed and configured
2. Docker installed
3. AWS account with appropriate permissions

### Step 1: Build and Push Docker Image
```bash
# Build the Docker image
docker build -t finance-ai-agent .

# Create ECR repository
aws ecr create-repository --repository-name finance-ai-agent

# Get your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-west-2

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push the image
docker tag finance-ai-agent:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finance-ai-agent:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finance-ai-agent:latest
```

### Step 2: Create App Runner Service
```bash
# Create App Runner service
aws apprunner create-service \
  --service-name finance-ai-agent \
  --source-configuration '{
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/service-role/AppRunnerECRAccessRole"
    },
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/finance-ai-agent:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8501"
      }
    }
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  }'
```

### Step 3: Set Environment Variables
```bash
# Update the service with environment variables
aws apprunner update-service \
  --service-arn <YOUR_SERVICE_ARN> \
  --source-configuration '{
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/service-role/AppRunnerECRAccessRole"
    },
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/finance-ai-agent:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8501",
        "RuntimeEnvironmentVariables": {
          "DYNAMODB_TABLE": "transactions",
          "AWS_REGION": "'$AWS_REGION'",
          "EMAIL_HOST": "imap.gmail.com",
          "EMAIL_USER": "your-email@gmail.com",
          "EMAIL_PASSWORD": "your-app-password",
          "OPENAI_API_KEY": "your-openai-key"
        }
      }
    }
  }'
```

## Option B: Static Web App (Amplify)

### Step 1: Convert Streamlit to Static Web App
The `streamlit_app/index.html` file contains a basic web interface. You'll need to enhance it with JavaScript to interact with your backend APIs.

### Step 2: Set up Amplify Backend
```bash
# Initialize Amplify (if not already done)
amplify init

# Add API for DynamoDB access
amplify add api

# Add authentication (optional)
amplify add auth

# Push the changes
amplify push
```

### Step 3: Deploy to Amplify
```bash
# Add hosting
amplify add hosting

# Publish
amplify publish
```

## Environment Variables Required

Your application requires these environment variables:

### For Streamlit App:
- `DYNAMODB_TABLE`: DynamoDB table name (default: "transactions")
- `AWS_REGION`: AWS region (default: "us-west-2")
- `EMAIL_HOST`: IMAP server hostname
- `EMAIL_USER`: Email username
- `EMAIL_PASSWORD`: Email app password
- `OPENAI_API_KEY`: OpenAI API key

### For Lambda Function:
- `EMAIL_HOST`: IMAP server hostname
- `EMAIL_PORT`: IMAP port (default: 993)
- `EMAIL_USER`: Email username
- `EMAIL_PASSWORD`: Email app password
- `IMAP_FOLDER`: Email folder (default: "INBOX")
- `DYNAMODB_TABLE`: DynamoDB table name
- `OPENAI_API_KEY`: OpenAI API key

## Security Considerations

1. **IAM Roles**: Ensure your App Runner service has appropriate IAM roles for DynamoDB access
2. **Secrets Management**: Use AWS Secrets Manager for sensitive environment variables
3. **VPC Configuration**: Consider placing your App Runner service in a VPC for enhanced security

## Monitoring and Logging

1. **CloudWatch Logs**: App Runner automatically sends logs to CloudWatch
2. **Metrics**: Monitor CPU, memory, and request metrics
3. **Alerts**: Set up CloudWatch alarms for error rates and performance

## Cost Optimization

1. **Auto Scaling**: Configure App Runner auto-scaling based on CPU/memory usage
2. **Reserved Capacity**: Consider reserved capacity for predictable workloads
3. **Resource Limits**: Set appropriate CPU and memory limits

## Troubleshooting

### Common Issues:
1. **Port Configuration**: Ensure the correct port (8501) is exposed
2. **Environment Variables**: Verify all required variables are set
3. **DynamoDB Permissions**: Check IAM roles for DynamoDB access
4. **Health Checks**: Ensure the health check endpoint responds correctly

### Debug Commands:
```bash
# Check App Runner service status
aws apprunner describe-service --service-arn <SERVICE_ARN>

# View logs
aws logs describe-log-groups --log-group-name-prefix /aws/apprunner

# Test health check
curl https://your-app-runner-url/health
```

## Next Steps

1. Choose your deployment option (App Runner recommended)
2. Set up your environment variables
3. Deploy using the provided scripts
4. Test the application functionality
5. Set up monitoring and alerts
6. Configure CI/CD pipeline for automated deployments 