# AWS App Runner Deployment Guide

This guide will walk you through deploying your Streamlit app to AWS App Runner using the web console.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Docker** installed on your local machine
3. **AWS CLI** configured with credentials
4. **Git repository** with your code

## Step 1: Build and Push Docker Image

### Option A: Using the Automated Script

```bash
# Make sure you're in your project directory
cd /path/to/finance-ai-agent

# Run the deployment script
./deploy-app-runner.sh
```

### Option B: Manual Steps

```bash
# 1. Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
REPOSITORY_NAME="finance-ai-agent"

# 2. Create ECR repository
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION

# 3. Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# 4. Build Docker image
docker build -t $REPOSITORY_NAME .

# 5. Tag for ECR
docker tag $REPOSITORY_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest

# 6. Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest
```

## Step 2: Create App Runner Service (Web Console)

1. **Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner/)**

2. **Click "Create service"**

3. **Choose "Container registry"**

4. **Select "Amazon ECR"**

5. **Configure the service:**

   **Basic Settings:**
   - **Service name**: `finance-ai-agent`
   - **Port**: `8501`
   - **CPU**: `1 vCPU`
   - **Memory**: `2 GB`

   **Environment Variables:**
   - `EMAIL_HOST` = `imap.gmail.com`
   - `EMAIL_USER` = `your-email@gmail.com`
   - `EMAIL_PASSWORD` = `your-app-password`
   - `DYNAMODB_TABLE` = `transactions`
   - `OPENAI_API_KEY` = `your-openai-api-key`

6. **Click "Create & deploy"**

## Step 3: Wait for Deployment

- The service will take 5-10 minutes to deploy
- You can monitor progress in the App Runner console
- Once complete, you'll get a service URL

## Step 4: Set Up Backend Services

### A. Create DynamoDB Table

1. Go to [DynamoDB Console](https://console.aws.amazon.com/dynamodb/)
2. Click **"Create table"**
3. **Table name**: `transactions`
4. **Partition key**: `txn_id` (String)
5. **Settings**: Choose **"Customize settings"**
6. **Capacity mode**: **"On-demand"**
7. Click **"Create table"**

### B. Create Lambda Function

1. Go to [Lambda Console](https://console.aws.amazon.com/lambda/)
2. Click **"Create function"**
3. **Function name**: `finance-email-fetcher`
4. **Runtime**: `Python 3.12`
5. Click **"Create function"**

### C. Upload Lambda Code

1. In your Lambda function, go to the **"Code"** tab
2. Click **"Upload from"** → **".zip file"**
3. Upload the `lambda-deployment.zip` file (build it first using `./build-lambda.sh`)

### D. Configure Lambda Environment Variables

In your Lambda function, go to **"Configuration"** → **"Environment variables"** and add:
- `EMAIL_HOST` = `imap.gmail.com`
- `EMAIL_USER` = `your-email@gmail.com`
- `EMAIL_PASSWORD` = `your-app-password`
- `DYNAMODB_TABLE` = `transactions`
- `OPENAI_API_KEY` = `your-openai-api-key`

### E. Set Up EventBridge Rule

1. Go to [EventBridge Console](https://console.aws.amazon.com/events/)
2. Click **"Create rule"**
3. **Name**: `daily-email-fetch`
4. **Schedule**: `rate(1 day)`
5. **Target**: Select your Lambda function
6. Click **"Create"**

## Step 5: Test Your Deployment

1. **Access your app**: Use the App Runner service URL
2. **Test Lambda**: Manually invoke the Lambda function
3. **Check DynamoDB**: Verify data is being stored

## Troubleshooting

### Common Issues:

1. **Image Build Fails**:
   - Check Dockerfile syntax
   - Verify all dependencies are in requirements.txt
   - Check build logs in App Runner console

2. **Service Won't Start**:
   - Verify port 8501 is exposed in Dockerfile
   - Check environment variables are set correctly
   - Review App Runner logs

3. **Environment Variables Not Working**:
   - Verify they're set in App Runner console
   - Check variable names match your code
   - Restart the service after changing variables

4. **Lambda Function Issues**:
   - Check CloudWatch logs for errors
   - Verify all environment variables are set
   - Test the Lambda function manually first

### Debugging Commands:

```bash
# Check App Runner service status
aws apprunner describe-service --service-arn YOUR_SERVICE_ARN --region us-east-1

# Check ECR repository
aws ecr describe-repositories --repository-names finance-ai-agent --region us-east-1

# Test Docker build locally
docker build -t finance-ai-agent .
docker run -p 8501:8501 finance-ai-agent

# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/finance-email-fetcher"
```

## Cost Optimization

1. **App Runner**: ~$13/month for 1 vCPU, 2 GB memory
2. **DynamoDB**: Pay-per-request pricing
3. **Lambda**: Free tier includes 1M requests/month
4. **EventBridge**: Free tier includes 1M events/month

## Monitoring

Set up CloudWatch alarms for:
- App Runner service health
- Lambda function errors
- DynamoDB throttling
- Email processing failures

## Next Steps

1. Set up custom domain
2. Configure SSL certificates
3. Set up monitoring and alerting
4. Implement backup strategies
5. Add authentication if needed 