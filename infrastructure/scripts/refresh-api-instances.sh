#!/bin/bash
set -e

echo "🔄 Refreshing EC2 API instances with new configuration..."

# Get ASG name
ASG_NAME=$(aws autoscaling describe-auto-scaling-groups \
    --region us-west-2 \
    --query 'AutoScalingGroups[?contains(AutoScalingGroupName, `nexus-ai-api-asg`)].AutoScalingGroupName' \
    --output text)

if [ -z "$ASG_NAME" ]; then
    echo "❌ Error: Could not find Auto Scaling Group"
    exit 1
fi

echo "📋 Found ASG: $ASG_NAME"

# Start instance refresh
REFRESH_ID=$(aws autoscaling start-instance-refresh \
    --region us-west-2 \
    --auto-scaling-group-name "$ASG_NAME" \
    --preferences '{"MinHealthyPercentage": 50, "InstanceWarmup": 300}' \
    --query 'InstanceRefreshId' \
    --output text)

echo "✅ Instance refresh started: $REFRESH_ID"
echo "⏳ Waiting for refresh to complete (this may take 5-10 minutes)..."

# Wait for refresh to complete
while true; do
    STATUS=$(aws autoscaling describe-instance-refreshes \
        --region us-west-2 \
        --auto-scaling-group-name "$ASG_NAME" \
        --instance-refresh-ids "$REFRESH_ID" \
        --query 'InstanceRefreshes[0].Status' \
        --output text)
    
    PERCENTAGE=$(aws autoscaling describe-instance-refreshes \
        --region us-west-2 \
        --auto-scaling-group-name "$ASG_NAME" \
        --instance-refresh-ids "$REFRESH_ID" \
        --query 'InstanceRefreshes[0].PercentageComplete' \
        --output text)
    
    echo "Status: $STATUS - Progress: ${PERCENTAGE}%"
    
    if [ "$STATUS" = "Successful" ]; then
        echo "✅ Instance refresh completed successfully!"
        break
    elif [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Cancelled" ]; then
        echo "❌ Instance refresh failed with status: $STATUS"
        exit 1
    fi
    
    sleep 30
done

echo ""
echo "🎉 All done! Testing API endpoint..."
sleep 10

# Test API
curl -s http://nexus-ai-alb-prod-1209340498.us-west-2.elb.amazonaws.com/api/v1/statistics/overview | jq .
