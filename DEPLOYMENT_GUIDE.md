# AWS Amplify Deployment Guide for Finance AI Agent

This guide will walk you through deploying the Finance AI Agent to AWS Amplify.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Amplify CLI** installed: `npm install -g @aws-amplify/cli`
4. **GitHub repository** with your code
5. **Environment variables** ready (see Configuration section)

## Step 1: Prepare Your Environment Variables

Create a `.env` file in your project root:

```bash
# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
IMAP_FOLDER=INBOX

# AWS Configuration
DYNAMODB_TABLE=transactions
AWS_REGION=us-east-1

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
```

## Step 2: Initialize Amplify Project

```bash
# Initialize Amplify in your project
amplify init

# Follow the prompts:
# - Enter a name for the project: finance-ai-agent
# - Enter a name for the environment: dev
# - Choose your default editor
# - Choose JavaScript as the type of app
# - Choose React as the framework
# - Choose No for source code management
# - Choose No for distribution settings
# - Choose No for build settings
```

## Step 3: Add Backend Services

```bash
# Add API (AppSync)
amplify add api

# Choose GraphQL
# Choose API key as authentication type
# Choose No for advanced settings
# Choose No for conflict detection
# Choose Yes to generate code

# Add Lambda Function
amplify add function

# Choose Lambda
# Enter function name: emailFetcher
# Choose NodeJS runtime
# Choose No for advanced settings
# Choose No for Lambda layers
# Choose No for environment variables (we'll add them later)

# Add Storage (DynamoDB)
amplify add storage

# Choose DynamoDB
# Choose No for advanced settings
# Choose No for additional settings
```

## Step 4: Configure Environment Variables

In the Amplify Console:

1. Go to your app → Backend environments → dev
2. Navigate to Functions → emailFetcher
3. Add environment variables:
   - `EMAIL_HOST`: `imap.gmail.com`
   - `EMAIL_USER`: Your email address
   - `EMAIL_PASSWORD`: Your app password
   - `DYNAMODB_TABLE`: `transactions`
   - `OPENAI_API_KEY`: Your OpenAI API key

## Step 5: Deploy Backend Services

```bash
# Push backend services to AWS
amplify push

# This will create:
# - DynamoDB table
# - Lambda function
# - AppSync API
# - IAM roles and policies
```

## Step 6: Build and Deploy Frontend

```bash
# Build Lambda deployment package
chmod +x build-lambda.sh
./build-lambda.sh

# Deploy Lambda function with the built package
aws lambda update-function-code \
    --function-name dev-emailFetcher \
    --zip-file fileb://lambda-deployment.zip

# Push to Amplify
amplify push
```

## Step 7: Configure Amplify Build Settings

In the Amplify Console:

1. Go to Build settings
2. Replace the build commands with:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - echo "Installing dependencies..."
        - pip install -r requirements.txt
    build:
      commands:
        - echo "Building Streamlit app..."
        - mkdir -p dist
        - cp -r streamlit_app/* dist/
        - cp -r extractor dist/
        - cp -r shared dist/
        - cp requirements.txt dist/
        - cp Dockerfile dist/
        - echo "Build completed"
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
      - .venv/**/*
```

## Step 8: Set Up EventBridge Rule

Create an EventBridge rule to trigger the Lambda function daily:

```bash
# Create EventBridge rule
aws events put-rule \
    --name daily-email-fetch \
    --schedule-expression "rate(1 day)" \
    --description "Trigger email fetcher daily"

# Add Lambda as target
aws events put-targets \
    --rule daily-email-fetch \
    --targets "Id"="1","Arn"="$(aws lambda get-function --function-name dev-emailFetcher --query 'Configuration.FunctionArn' --output text)"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name dev-emailFetcher \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "$(aws events describe-rule --name daily-email-fetch --query 'Arn' --output text)"
```

## Step 9: Test the Deployment

1. **Test Lambda Function**:
   ```bash
   aws lambda invoke \
       --function-name dev-emailFetcher \
       --payload '{}' \
       response.json
   ```

2. **Test DynamoDB**:
   ```bash
   aws dynamodb scan --table-name transactions
   ```

3. **Access the App**: Your app will be available at the Amplify-provided URL

## Troubleshooting

### Common Issues:

1. **Lambda Function Too Large**:
   - The deployment package might exceed Lambda's limit
   - Solution: Use Lambda layers for dependencies

2. **Environment Variables Not Set**:
   - Check Amplify Console → Backend → Functions
   - Ensure all required variables are configured

3. **DynamoDB Permissions**:
   - Verify IAM roles have proper DynamoDB permissions
   - Check CloudWatch logs for permission errors

4. **Email Connection Issues**:
   - Verify email credentials
   - Check if app password is required for Gmail
   - Test IMAP connection manually

### Debugging:

```bash
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/dev-emailFetcher"

# Check DynamoDB table
aws dynamodb describe-table --table-name transactions

# Test email connection
python -c "
import imaplib
import ssl
context = ssl.create_default_context()
conn = imaplib.IMAP4_SSL('imap.gmail.com', 993, ssl_context=context)
conn.login('your-email@gmail.com', 'your-app-password')
print('Connection successful')
conn.logout()
"
```

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to Git
2. **IAM Roles**: Use least privilege principle
3. **API Keys**: Rotate regularly
4. **Email Security**: Use app passwords, not regular passwords

## Cost Optimization

1. **DynamoDB**: Use on-demand billing for development
2. **Lambda**: Monitor execution time and memory usage
3. **EventBridge**: Free tier includes 1 million events/month
4. **Amplify**: Free tier includes 15 build minutes/month

## Monitoring

Set up CloudWatch alarms for:
- Lambda function errors
- DynamoDB throttling
- Email processing failures
- API response times

## Next Steps

1. Set up custom domain
2. Configure SSL certificates
3. Set up monitoring and alerting
4. Implement backup strategies
5. Add authentication if needed 