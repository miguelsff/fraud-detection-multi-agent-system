#!/bin/bash
# Health check script - Verify deployment is healthy

set -e

ENVIRONMENT=${1:-dev}

echo "🏥 Running health checks for environment: $ENVIRONMENT"

# Configuration
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Get URLs from Terraform outputs
echo "🔍 Getting endpoints from Terraform..."
BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null) || {
    echo "❌ Failed to get backend URL. Has infrastructure been deployed?"
    exit 1
}

FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null) || {
    echo "❌ Failed to get frontend URL"
    exit 1
}

DATABASE_FQDN=$(terraform output -raw database_fqdn 2>/dev/null) || {
    echo "❌ Failed to get database FQDN"
    exit 1
}

cd ../../..

echo "✅ Endpoints retrieved"
echo ""

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl."
    exit 1
fi

# Function to check HTTP endpoint
check_http() {
    local NAME=$1
    local URL=$2
    local PATH=$3

    echo -n "🔍 Checking $NAME... "

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "${URL}${PATH}" 2>/dev/null) || {
        echo "❌ FAILED (connection error)"
        return 1
    }

    if [ "$STATUS" = "200" ]; then
        echo "✅ OK (HTTP $STATUS)"
        return 0
    else
        echo "❌ FAILED (HTTP $STATUS)"
        return 1
    fi
}

# Run health checks
echo "🏥 Health Checks:"
echo "────────────────────────────────────────"

check_http "Backend Health" "$BACKEND_URL" "/api/v1/health"
BACKEND_RESULT=$?

check_http "Frontend" "$FRONTEND_URL" "/"
FRONTEND_RESULT=$?

# Database check (requires psql)
echo -n "🔍 Checking Database... "
if command -v psql &> /dev/null; then
    # Note: This won't work from outside Azure without VPN/bastion
    echo "⚠️  SKIPPED (requires VPN or bastion access)"
else
    echo "⚠️  SKIPPED (psql not installed)"
fi

# Summary
echo ""
echo "📊 Summary:"
echo "────────────────────────────────────────"

TOTAL=2
PASSED=0

[ $BACKEND_RESULT -eq 0 ] && ((PASSED++))
[ $FRONTEND_RESULT -eq 0 ] && ((PASSED++))

echo "Passed: $PASSED / $TOTAL"

if [ $PASSED -eq $TOTAL ]; then
    echo "✅ All health checks passed!"
    exit 0
else
    echo "❌ Some health checks failed"
    exit 1
fi
