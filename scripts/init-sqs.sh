#!/bin/bash
echo "Creating SQS queue: analytics-queue"
awslocal sqs create-queue --queue-name analytics-queue --region us-east-1
echo "SQS queue created"
