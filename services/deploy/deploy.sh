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

  # Accept both unversioned and versioned Key Vault secret URIs.
  if [[ "$kvref" =~ ^keyvaultref:https://([^.]+)\.vault\.azure\.net/secrets/([^/]+)(/[^/]+)?$ ]]; then
    if az keyvault secret show \
      --vault-name "${BASH_REMATCH[1]}" \
      --name "${BASH_REMATCH[2]}" \
      --query "value" \
      --output tsv 2>/dev/null; then
      return
    fi
    echo "⚠️ Could not read ACR password from Key Vault; falling back to ACR admin credentials" >&2
  elif [ -n "$kvref" ] && [[ ! "$kvref" =~ ^keyvaultref: ]]; then
    echo "$kvref"
    return
  fi

  az acr credential show \
    --name "$(get_yaml_value_from_file "$file" "AZ_ACR_NAME")" \
    --subscription "$(get_yaml_value_from_file "$file" "AZ_SUBSCRIPTION_ID")" \
    --query "passwords[0].value" \
    --output tsv
}

# Build env/secret strings from an explicit allow-list of variables.yml keys.
# Prints env line, then "---", then secrets line.
build_env_and_secrets() {
  local envs=""
  local secrets=""
  local key value env_key safe_secret_name

  for key in "$@"; do
    if [[ "$key" == PORT=* ]]; then
      envs+=" PORT=${key#PORT=}"
      continue
    fi

    value="$(get_yaml_value_from_file "$VARS_FILE" "$key")"
    if [ -z "$value" ]; then
      continue
    fi

    env_key="${key//-/_}"
    safe_secret_name=$(echo "$key" | tr '[:upper:]' '[:lower:]' | tr -d '_')

    if [[ "$value" =~ ^keyvaultref: ]]; then
      secrets+=" ${safe_secret_name}=${value},identityref:system"
      envs+=" ${env_key}=secretref:${safe_secret_name}"
    else
      envs+=" ${env_key}=${value}"
    fi
  done

  envs="$(echo "$envs" | xargs)"
  secrets="$(echo "$secrets" | xargs)"

  echo "$envs"
  echo "---"
  echo "$secrets"
}

app_exists() {
  az containerapp show \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$1" \
    --subscription "$AZ_SUBSCRIPTION_ID" \
    >/dev/null 2>&1
}

deploy_service() {
  local containerapp_name="$1"
  local source_repo="$2"
  local port="$3"
  local ingress="$4"
  shift 4
  local env_keys=("$@")

  local image_full="${AZ_ACR_LOGIN_SERVER}/${source_repo}:${TAG_RELEASE}"
  echo "🚀 Deploying $image_full to container app: $containerapp_name"

  local tmp_output envs secrets
  tmp_output=$(build_env_and_secrets "${env_keys[@]}" "PORT=${port}")
  envs=$(echo "$tmp_output" | sed -n '1p')
  secrets=$(echo "$tmp_output" | sed -n '3p')

  if app_exists "$containerapp_name"; then
    echo "ℹ️ Updating existing app $containerapp_name"

    if [ -n "$secrets" ]; then
      # update does not accept --secrets
      az containerapp secret set \
        --name "$containerapp_name" \
        --resource-group "$AZ_RESOURCE_GROUP" \
        --subscription "$AZ_SUBSCRIPTION_ID" \
        --secrets $secrets
    fi

    az containerapp registry set \
      --name "$containerapp_name" \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --subscription "$AZ_SUBSCRIPTION_ID" \
      --server "$AZ_ACR_LOGIN_SERVER" \
      --username "$AZ_ACR_NAME" \
      --password "$AZ_ACR_PASSWORD" \
      --only-show-errors >/dev/null

    az containerapp update \
      --name "$containerapp_name" \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --subscription "$AZ_SUBSCRIPTION_ID" \
      --image "$image_full" \
      --set-env-vars $envs \
      --container-name "$containerapp_name" \
      --cpu 0.5 --memory 1.0Gi \
      --min-replicas "$MIN_REPLICAS" --max-replicas "$MAX_REPLICAS"

    az containerapp ingress update \
      --name "$containerapp_name" \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --subscription "$AZ_SUBSCRIPTION_ID" \
      --target-port "$port" \
      --type "$ingress"
  else
    echo "ℹ️ Creating container app $containerapp_name"
    local create_args=(
      --name "$containerapp_name"
      --resource-group "$AZ_RESOURCE_GROUP"
      --subscription "$AZ_SUBSCRIPTION_ID"
      --environment "$AZ_CONTAINERAPP_ENV_NAME"
      --image "$image_full"
      --env-vars $envs
      --target-port "$port"
      --ingress "$ingress"
      --cpu 0.5 --memory 1.0Gi
      --min-replicas "$MIN_REPLICAS" --max-replicas "$MAX_REPLICAS"
      --registry-server "$AZ_ACR_LOGIN_SERVER"
      --registry-username "$AZ_ACR_NAME"
      --registry-password "$AZ_ACR_PASSWORD"
      --system-assigned
      --scale-rule-name http-concurrency
      --scale-rule-http-concurrency 8
    )
    if [ -n "$secrets" ]; then
      az containerapp create "${create_args[@]}" --secrets $secrets
    else
      az containerapp create "${create_args[@]}"
    fi
  fi

  local fqdn
  fqdn=$(az containerapp show \
    --name "$containerapp_name" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --subscription "$AZ_SUBSCRIPTION_ID" \
    --query "properties.configuration.ingress.fqdn" -o tsv)
  echo "✅ Deployed $containerapp_name → https://${fqdn}"
}

TAG_RELEASE="latest"

AZ_SUBSCRIPTION_ID="$(get_yaml_value_from_file "$VARS_FILE" "AZ_SUBSCRIPTION_ID")"
AZ_RESOURCE_GROUP="$(get_yaml_value_from_file "$VARS_FILE" "AZ_RESOURCE_GROUP")"
AZ_CONTAINERAPP_ENV_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_ENV_NAME")"
AZ_ACR_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_NAME")"
AZ_ACR_LOGIN_SERVER="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_LOGIN_SERVER")"
AZ_ACR_PASSWORD="$(get_acr_password "$VARS_FILE")"
MIN_REPLICAS="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_MIN_REPLICAS")"
MAX_REPLICAS="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_MAX_REPLICAS")"

PROFILE_APP="$(get_yaml_value_from_file "$VARS_FILE" "PROFILE_CONTAINER_APP_NAME")"
TASK_APP="$(get_yaml_value_from_file "$VARS_FILE" "TASK_CONTAINER_APP_NAME")"
TIMELOG_APP="$(get_yaml_value_from_file "$VARS_FILE" "TIMELOG_CONTAINER_APP_NAME")"
PROFILE_PORT="$(get_yaml_value_from_file "$VARS_FILE" "PROFILE_SERVICE_PORT")"
TASK_PORT="$(get_yaml_value_from_file "$VARS_FILE" "TASK_SERVICE_PORT")"
TIMELOG_PORT="$(get_yaml_value_from_file "$VARS_FILE" "TIMELOG_SERVICE_PORT")"

SHARED_ENV_KEYS=(
  KEY_VAULT_URL
  JWT_PUBLIC_KEY_SECRET_NAME
  JWT_KID_SECRET_NAME
  CORS_ALLOWED_ORIGIN
  USE_LOCAL_KEY
  JWT_ISSUER
  AZURE_STORAGE_CONNECTION_STRING
)

PROFILE_ENV_KEYS=(
  "${SHARED_ENV_KEYS[@]}"
  USERS_TABLE_NAME
  JWT_PRIVATE_KEY_SECRET_NAME
  JWT_EXPIRY_HOURS
  ADMIN_EMAILS
  ALLOWED_EMAIL_DOMAIN
  AUTH_RATE_LIMIT_PER_MINUTE
)

TASK_ENV_KEYS=(
  "${SHARED_ENV_KEYS[@]}"
  TASKS_TABLE_NAME
  PROFILE_SERVICE_BASE_URL
  VALIDATE_ASSIGN_EMAILS_WITH_PROFILE_SERVICE
  PROFILE_SERVICE_TIMEOUT_SECONDS
  DEFAULT_ADMIN_LIST_PAGE_SIZE
)

TIMELOG_ENV_KEYS=(
  "${SHARED_ENV_KEYS[@]}"
  TIMESHEET_TABLE_NAME
  PROFILE_SERVICE_BASE_URL
  TASK_SERVICE_BASE_URL
)

if [ -z "$AZ_SUBSCRIPTION_ID" ] || [ -z "$AZ_RESOURCE_GROUP" ] || [ -z "$AZ_CONTAINERAPP_ENV_NAME" ] || \
   [ -z "$AZ_ACR_NAME" ] || [ -z "$AZ_ACR_LOGIN_SERVER" ] || \
   [ -z "$MIN_REPLICAS" ] || [ -z "$MAX_REPLICAS" ] || \
   [ -z "$PROFILE_APP" ] || [ -z "$TASK_APP" ] || [ -z "$TIMELOG_APP" ] || \
   [ -z "$PROFILE_PORT" ] || [ -z "$TASK_PORT" ] || [ -z "$TIMELOG_PORT" ]; then
  echo "❌ Missing required shared configuration in $VARS_FILE"
  exit 1
fi

deploy_service "$PROFILE_APP" "profile-service" "$PROFILE_PORT" "external" "${PROFILE_ENV_KEYS[@]}"
deploy_service "$TASK_APP" "task-service" "$TASK_PORT" "external" "${TASK_ENV_KEYS[@]}"
deploy_service "$TIMELOG_APP" "timelog-service" "$TIMELOG_PORT" "external" "${TIMELOG_ENV_KEYS[@]}"

echo "🎉 All 3 services deployed."
echo "   Inter-service: PROFILE_SERVICE_BASE_URL=$(get_yaml_value_from_file "$VARS_FILE" "PROFILE_SERVICE_BASE_URL")"
echo "   Inter-service: TASK_SERVICE_BASE_URL=$(get_yaml_value_from_file "$VARS_FILE" "TASK_SERVICE_BASE_URL")"
echo "   Public: $(get_yaml_value_from_file "$VARS_FILE" "VITE_PROFILE_SERVICE_BASE_URL")"
echo "   Public: $(get_yaml_value_from_file "$VARS_FILE" "VITE_TASK_SERVICE_BASE_URL")"
echo "   Public: $(get_yaml_value_from_file "$VARS_FILE" "VITE_TIMELOG_SERVICE_BASE_URL")"
