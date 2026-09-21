#!/bin/sh
set -eu

if [ -n "$(git status --porcelain --untracked-files=normal)" ]; then
  echo "Commit or stash source changes before building release images." >&2
  exit 1
fi

registry_name=$(azd env get-value AZURE_CONTAINER_REGISTRY_NAME)
if [ -z "$registry_name" ]; then
  echo "Run the bootstrap infrastructure provision first." >&2
  exit 1
fi

commit=$(git rev-parse --short=12 HEAD)
image_tag="git-${commit}"

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/gateway:${image_tag}" \
  --file infra/gateway/Dockerfile \
  .

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/web:${image_tag}" \
  --file apps/web/Dockerfile \
  --build-arg DEMO_GATE_REQUIRED=true \
  --build-arg NEXT_PUBLIC_MANOBAL_MODE=demo \
  .

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/engine:${image_tag}" \
  --file services/engine/Dockerfile \
  .

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/vault:${image_tag}" \
  --file services/vault/Dockerfile \
  .

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/realtime:${image_tag}" \
  --file infra/realtime/Dockerfile \
  .

az acr build \
  --registry "$registry_name" \
  --platform linux/amd64 \
  --image "manobal/synth:${image_tag}" \
  --file services/synth/Dockerfile \
  .

azd env set IMAGE_TAG "$image_tag"
echo "Release images built and recorded as ${image_tag}."
