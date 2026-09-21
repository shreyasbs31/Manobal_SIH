#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 RESOURCE_GROUP JOB_NAME" >&2
  exit 2
fi

resource_group=$1
job_name=$2
execution_name=$(az containerapp job start \
  --resource-group "$resource_group" \
  --name "$job_name" \
  --query name \
  --output tsv)

attempt=0
while [ "$attempt" -lt 240 ]; do
  status=$(az containerapp job execution show \
    --resource-group "$resource_group" \
    --job-name "$job_name" \
    --name "$execution_name" \
    --query properties.status \
    --output tsv)
  case "$status" in
    Succeeded)
      echo "Container Apps job succeeded: ${job_name}"
      exit 0
      ;;
    Failed | Stopped | Degraded)
      echo "Container Apps job failed: ${job_name} (${status})" >&2
      az containerapp job execution show \
        --resource-group "$resource_group" \
        --job-name "$job_name" \
        --name "$execution_name" \
        --output json >&2
      exit 1
      ;;
  esac
  attempt=$((attempt + 1))
  sleep 10
done

echo "Timed out waiting for Container Apps job: ${job_name}" >&2
exit 1
