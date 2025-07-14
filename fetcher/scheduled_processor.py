"""
Scheduled Lambda function to process emails daily
This function is triggered by EventBridge/CloudWatch Events
"""
import os
import json
import boto3
from datetime import datetime
from lambda_function import EmailProcessor

def lambda_handler(event, context):
    """
    Lambda handler for scheduled email processing
    Runs once per day to fetch and process emails
    """
    try:
        print(f"Starting scheduled email processing at {datetime.now()}")
        
        # Initialize the email processor
        processor = EmailProcessor()
        
        # Process emails
        processed_count = processor.process_emails()
        
        print(f"Successfully processed {processed_count} emails")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {processed_count} emails',
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error in scheduled processing: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        } 