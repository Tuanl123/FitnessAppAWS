#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  TEARDOWN: This will DESTROY all AWS resources   ║${NC}"
echo -e "${RED}║  including databases, containers, and all data.  ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
echo ""

if [ "${1:-}" != "--yes" ]; then
    read -p "Type 'destroy' to confirm: " CONFIRM
    if [ "$CONFIRM" != "destroy" ]; then
        echo -e "${YELLOW}Aborted.${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}[1/3] Emptying S3 bucket (if exists)...${NC}"
BUCKET=$(cd "$INFRA_DIR" && terraform output -raw frontend_bucket_name 2>/dev/null || true)
if [ -n "$BUCKET" ]; then
    aws s3 rm "s3://$BUCKET" --recursive 2>/dev/null || true
    echo "  Bucket emptied: $BUCKET"
else
    echo "  No bucket found (skipping)"
fi

echo -e "${YELLOW}[2/3] Running terraform destroy...${NC}"
cd "$INFRA_DIR"
terraform destroy -auto-approve

echo ""
echo -e "${YELLOW}[3/3] Cleaning up local state...${NC}"
rm -f terraform.tfstate terraform.tfstate.backup
rm -rf .terraform

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  All AWS resources have been destroyed.          ║${NC}"
echo -e "${GREEN}║  Your AWS account is clean.                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
