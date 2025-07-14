#!/bin/bash

# Setup Daily Email Processing Schedule
# This script creates an EventBridge rule to trigger email processing daily

set -e

echo "🕐 Setting up daily email processing schedule..."

# Configuration
AWS_REGION=${AWS_REGION:-"us-west-2"}
RULE_NAME="daily-email-processing"
FUNCTION_NAME="scheduledEmailProcessor"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $AWS_ACCOUNT_ID"

# Step 1: Create EventBridge rule
echo "📅 Creating EventBridge rule for daily processing..."
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "rate(1 day)" \
    --description "Trigger email processing daily" \
    --region $AWS_REGION

# Step 2: Create target for the rule
echo "🎯 Creating target for the rule..."
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $AWS_REGION

# Step 3: Add permission for EventBridge to invoke Lambda
echo "🔐 Adding permissions for EventBridge to invoke Lambda..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id "EventBridgeInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME" \
    --region $AWS_REGION

echo "✅ Daily schedule setup completed!"
echo "📅 Email processing will run once per day at midnight UTC"
echo ""
echo "📝 To modify the schedule:"
echo "   - Edit the rule: aws events put-rule --name $RULE_NAME --schedule-expression 'rate(1 day)'"
echo "   - Run every 6 hours: aws events put-rule --name $RULE_NAME --schedule-expression 'rate(6 hours)'"
echo "   - Run at specific time: aws events put-rule --name $RULE_NAME --schedule-expression 'cron(0 8 * * ? *)' (8 AM UTC daily)"
echo ""
echo "🔍 To monitor the schedule:"
echo "   - Check CloudWatch logs: aws logs describe-log-groups --log-group-name-prefix /aws/lambda/$FUNCTION_NAME"
echo "   - View EventBridge rules: aws events list-rules --name-prefix $RULE_NAME" 