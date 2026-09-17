set -euo pipefail
 
# help_text() {
#   echo "Usage: $0 <environment>"
#   echo "Builds and pushes a Docker image using variables.yaml"
#   echo ""
#   echo "- Arguments"
#   echo "environment: dev, test, prod"
#   echo ""
#   echo "Example: ./$0 dev"
# }
 
# if [ $# -ne 1 ]; then
#   help_text
#   exit 1
# fi
 
# ENVIRONMENT="$1"
 
# Resolve paths relative to this script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$BACKEND_V1_DIR/.." && pwd)"
# VERSION_FILE="$BACKEND_V1_DIR/version.yaml"
VARS_FILE="$ROOT_DIR/variables.yml"
 
# if [ ! -f "$VERSION_FILE" ]; then
#   echo "❌ version.yaml not found at: $VERSION_FILE"
#   exit 1
# fi
 
if [ ! -f "$VARS_FILE" ]; then
  echo "❌ variables file not found $VARS_FILE"
  exit 1
fi
 
get_yaml_value_from_file() {
  local file="$1"
  local key="$2"
  # Grep the exact key at line start, split by ': ', strip quotes and whitespace
  grep -E "^${key}:" "$file" | awk -F": " '{print $2}' | tr -d '"' | tr -d "'" | xargs || true
}
 
# Read required variables from variables.<env>.yaml (ACR, repo name, tag prefix)
AZ_ACR_NAME="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_NAME")"
AZ_ACR_LOGIN_SERVER="$(get_yaml_value_from_file "$VARS_FILE" "AZ_ACR_LOGIN_SERVER")"
# SOURCE="$(get_yaml_value_from_file "$VARS_FILE" "SOURCE")"
SERVICE1="profile-service"
SERVICE2="task-service"
SERVICE3="timelog-service"
# DOCKER_TAG="$(get_yaml_value_from_file "$VARS_FILE" "DOCKER_TAG")"
 
if [ -z "${AZ_ACR_NAME}" ] || [ -z "${AZ_ACR_LOGIN_SERVER}" ]; then
  echo "❌ Missing required values in $VARS_FILE. Ensure AZ_ACR_NAME, AZ_ACR_LOGIN_SERVER are set."
  exit 1
fi
 
# Read versions from version.yaml
# API_VERSION="$(get_yaml_value_from_file "$VERSION_FILE" "api_version")"
# RELEASE_VERSION="$(get_yaml_value_from_file "$VERSION_FILE" "release_version")"
 
# if [ -z "${API_VERSION}" ] || [ -z "${RELEASE_VERSION}" ]; then
#   echo "❌ Missing api_version or release_version in $VERSION_FILE"
#   exit 1
# fi
 
IMAGE_REPO_PS="${AZ_ACR_LOGIN_SERVER}/${SERVICE1}"
IMAGE_REPO_TS="${AZ_ACR_LOGIN_SERVER}/${SERVICE2}"
IMAGE_REPO_TLS="${AZ_ACR_LOGIN_SERVER}/${SERVICE3}"
# TAG_API="${API_VERSION}"
TAG_RELEASE="latest"
 
# echo "📦 Building image: $IMAGE_REPO"
# echo "🔖 Tags: $TAG_RELEASE"
 
az acr login -n "${AZ_ACR_NAME}"

# Profile Service
docker buildx build --platform linux/amd64 \
  -f "$BACKEND_V1_DIR/profile-service/Dockerfile" \
  -t "${IMAGE_REPO_PS}:${TAG_RELEASE}" \
  "$ROOT_DIR" --push

# Task Service
docker buildx build --platform linux/amd64 \
  -f "$BACKEND_V1_DIR/task-service/Dockerfile" \
  -t "${IMAGE_REPO_TS}:${TAG_RELEASE}" \
  "$ROOT_DIR" --push

# Timelog Service
docker buildx build --platform linux/amd64 \
  -f "$BACKEND_V1_DIR/timelog-service/Dockerfile" \
  -t "${IMAGE_REPO_TLS}:${TAG_RELEASE}" \
  "$ROOT_DIR" --push
 
echo "✅ Image pushed: ${IMAGE_REPO_PS}:${TAG_RELEASE}"
echo "✅ Image pushed: ${IMAGE_REPO_TS}:${TAG_RELEASE}"
echo "✅ Image pushed: ${IMAGE_REPO_TLS}:${TAG_RELEASE}"
 