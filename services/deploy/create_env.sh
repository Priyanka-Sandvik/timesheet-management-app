set -euo pipefail
 
# help_text() {
#   echo "Usage: $0 <backend> <environment>"
#   echo "Creates a Container Apps environment using variables.<env>.yaml"
#   echo ""
#   echo "- Arguments"
#   echo "backend: srp, ugd"
#   echo "environment: dev, test, prod"
#   echo ""
#   echo "Example: ./$0 srp dev"
# }
 
# if [ $# -ne 2 ]; then
#   help_text
#   exit 1
# fi
 
# BACKEND="$1"
# ENVIRONMENT="$2"
 
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$BACKEND_V1_DIR/.." && pwd)"
# VERSION_FILE="$BACKEND_V1_DIR/version.yaml"
VARS_FILE="$ROOT_DIR/variables.yml"
 
if [ ! -f "$VARS_FILE" ]; then
  echo "❌ variables file not found $VARS_FILE"
  exit 1
fi
 
get_yaml_value_from_file() {
  local file="$1"
  local key="$2"
  grep -E "^${key}:" "$file" | awk -F": " '{print $2}' | tr -d '"' | tr -d "'" | xargs || true
}
 
AZ_CONTAINERAPP_ENV_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_CONTAINERAPP_ENV_NAME")"
AZ_RESOURCE_GROUP="$(get_yaml_value_from_file "$VARS_FILE" "AZ_RESOURCE_GROUP")"
 
if [ -z "${AZ_CONTAINERAPP_ENV_NAME}" ] || [ -z "${AZ_RESOURCE_GROUP}" ]; then
  echo "❌ Missing required values in $VARS_FILE."
  echo "Required: AZ_CONTAINERAPP_ENV_NAME, AZ_RESOURCE_GROUP"
  exit 1
fi
 
LOCATION="westeurope"
 
echo "🚀 Creating Container Apps Environment"
echo "🏷 Name: $AZ_CONTAINERAPP_ENV_NAME"
echo "📁 Resource Group: $AZ_RESOURCE_GROUP"
echo "📍 Location: $LOCATION"
 
az containerapp env create \
  --name "$AZ_CONTAINERAPP_ENV_NAME" \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --location "$LOCATION"
 
echo "✅ Container Apps environment created successfully"