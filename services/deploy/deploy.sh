#!/bin/bash
set -euo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$BACKEND_V1_DIR/.." && pwd)"
VARS_FILE="$ROOT_DIR/variables.yml"

if [ ! -f "$VARS_FILE" ]; then
  echo "❌ variables file not found : $VARS_FILE"
  exit 1
fi

get_yaml_value_from_file() {
  local file="$1"
  local key="$2"
  grep -E "^${key}:" "$file" | awk -F": " '{print $2}' | tr -d '"' | tr -d "'" | xargs || true
}

get_acr_password() {
  local file="$1"
  local kvref
  kvref="$(get_yaml_value_from_file "$file" "AZ_ACR_PASSWORD")"

  if [[ "$kvref" =~ ^keyvaultref:https://([^.]+)\.vault\.azure\.net/secrets/([^/]+)$ ]]; then
    az keyvault secret show \
      --vault-name "${BASH_REMATCH[1]}" \
      --name "${BASH_REMATCH[2]}" \
      --query "value" \
      --output tsv
    return
  fi

  if [ -n "$kvref" ]; then
    echo "$kvref"
    return
  fi

  echo "❌ AZ_ACR_PASSWORD is missing or invalid in $file" >&2
  exit 1
}

TAG_RELEASE="latest"

# ---------------------------------------------------
# Load SHARED values
# ---------------------------------------------------
AZ_RESOURCE_GROUP="$(get_yaml_value_from_file "$VARS_FILE" "AZ_RESOURCE_GROUP")"
AZ_CONTAINERAPP_ENV_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_ENV_NAME")"
AZ_ACR_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_NAME")"
AZ_ACR_LOGIN_SERVER="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_LOGIN_SERVER")"
AZ_ACR_PASSWORD="$(get_acr_password "$VARS_FILE")"
MIN_REPLICAS="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_MIN_REPLICAS")"
MAX_REPLICAS="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_MAX_REPLICAS")"

if [ -z "$AZ_RESOURCE_GROUP" ] || [ -z "$AZ_CONTAINERAPP_ENV_NAME" ] || \
   [ -z "$AZ_ACR_NAME" ] || [ -z "$AZ_ACR_LOGIN_SERVER" ] || \
   [ -z "$MIN_REPLICAS" ] || [ -z "$MAX_REPLICAS" ]; then
  echo "❌ Missing required shared configuration in $VARS_FILE"
  exit 1
fi

# ---------------------------------------------------
# Build environment and secrets 
# ---------------------------------------------------
build_env_and_secrets() {
  local file="$1"
  local envs=""
  local secrets=""

  while IFS=: read -r raw_key raw_value; do
    key=$(echo "$raw_key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    value=$(echo "$raw_value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -z "$key" ]] || [[ "$key" =~ ^# ]]; then
      continue
    fi
    value=$(echo "$value" | sed 's/^"\(.*\)"$/\1/; s/^'\''\(.*\)'\''$/\1/')

    if [[ "$key" == "AZ_ACR_PASSWORD" || "$key" == "AZ-ACR-PASSWORD" ]]; then
      continue
    fi

    env_key="${key//-/_}"
    safe_secret_name=$(echo "$key" | tr '[:upper:]' '[:lower:]' | tr -d '_')

    if [[ "$value" =~ ^keyvaultref: ]]; then
      secrets+=" ${safe_secret_name}=${value},identityref:system"
      envs+=" ${env_key}=secretref:${safe_secret_name}"
    else
      if [ -n "$value" ]; then
        envs+=" ${env_key}=${value}"
      fi
    fi

  done < <(grep -E '^[A-Z0-9_-]+:' "$file")

  envs="$(echo "$envs" | xargs)"
  secrets="$(echo "$secrets" | xargs)"

  echo "$envs"
  echo "---"
  echo "$secrets"
}

# ---------------------------------------------------
# Deploy a service (update, fallback to create)
# ---------------------------------------------------
deploy_service() {
  local containerapp_name="$1"
  local source_repo="$2"
  local port="$3"
  local ingress="$4"

  local image_full="${AZ_ACR_LOGIN_SERVER}/${source_repo}:${TAG_RELEASE}"
  echo "🚀 Deploying $image_full to container app: $containerapp_name"

  local tmp_output envs secrets
  tmp_output=$(build_env_and_secrets "$VARS_FILE")
  envs=$(echo "$tmp_output" | sed -n '1p')
  secrets=$(echo "$tmp_output" | sed -n '3p')

  set +e
  az containerapp update \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$containerapp_name" \
    --image "$image_full" \
    --set-env-vars $envs \
    --secrets $secrets \
    --container-name "$containerapp_name" \
    --registry-server "$AZ_ACR_LOGIN_SERVER" \
    --registry-username "$AZ_ACR_NAME" \
    --registry-password "$AZ_ACR_PASSWORD" >/dev/null 2>&1
  status=$?
  set -e

  if [ $status -ne 0 ]; then
    echo "ℹ️ $containerapp_name not found or update failed. Creating new container app..."
    az containerapp create \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$containerapp_name" \
      --environment "$AZ_CONTAINERAPP_ENV_NAME" \
      --image "$image_full" \
      --secrets $secrets \
      --env-vars $envs \
      --target-port "$port" \
      --ingress "$ingress" \
      --cpu 0.5 --memory 1.0Gi \
      --min-replicas "$MIN_REPLICAS" --max-replicas "$MAX_REPLICAS" \
      --registry-server "$AZ_ACR_LOGIN_SERVER" \
      --registry-username "$AZ_ACR_NAME" \
      --registry-password "$AZ_ACR_PASSWORD" \
      --system-assigned \
      --scale-rule-name http-concurrency \
      --scale-rule-http-concurrency 8
  fi

  echo "✅ Deployed image: $image_full to $containerapp_name"
}

# ---------------------------------------------------
# Service registry: containerapp-name : acr-repo : port : ingress
# Naming convention: timesheet-int-<service>-ca
# ---------------------------------------------------
SERVICES=(
  "timesheet-int-profile-service-ca:profile-service:$(get_yaml_value_from_file "$VARS_FILE" "PROFILE_SERVICE_PORT"):external"
  "timesheet-int-task-service-ca:task-service:$(get_yaml_value_from_file "$VARS_FILE" "TASK_SERVICE_PORT"):external"
  "timesheet-int-timelog-service-ca:timelog-service:$(get_yaml_value_from_file "$VARS_FILE" "TIMELOG_SERVICE_PORT"):external"
)

for entry in "${SERVICES[@]}"; do
  IFS=":" read -r NAME REPO PORT INGRESS <<< "$entry"
  if [ -z "$PORT" ]; then
    echo "❌ Missing port for $NAME"
    exit 1
  fi
  deploy_service "$NAME" "$REPO" "$PORT" "$INGRESS"
done

echo "🎉 All 3 services deployed."
