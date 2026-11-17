#!/usr/bin/env bash
# Refresh the self-hosted Swagger UI and Redoc assets that the backend serves
# for /docs and /redoc (backend/app/static/api-docs/). The API docs must work
# with no internet connection, so FastAPI's default CDN URLs are never used.
#
# Maintenance only: needs npm and network access, and is NOT part of install
# or start-up. The files it writes are committed. Pin new versions with:
#   SWAGGER_UI_VERSION=5.x.y REDOC_VERSION=2.x.y scripts/vendor_api_docs.sh
# then run the backend tests and open /docs and /redoc once offline.
set -euo pipefail
cd "$(dirname "$0")/.."

SWAGGER_UI_VERSION="${SWAGGER_UI_VERSION:-5.35.0}"
REDOC_VERSION="${REDOC_VERSION:-2.5.4}"
dest=backend/app/static/api-docs

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp:?}"' EXIT

# npm verifies each tarball against the registry's integrity hash.
(cd "$tmp" && npm pack --silent "swagger-ui-dist@${SWAGGER_UI_VERSION}" "redoc@${REDOC_VERSION}" >/dev/null)
mkdir -p "$tmp/swagger" "$tmp/redoc" "$dest"
tar -xzf "$tmp/swagger-ui-dist-${SWAGGER_UI_VERSION}.tgz" -C "$tmp/swagger"
tar -xzf "$tmp/redoc-${REDOC_VERSION}.tgz" -C "$tmp/redoc"

swagger="$tmp/swagger/package"
redoc="$tmp/redoc/package"
cp "$swagger/swagger-ui-bundle.js" "$swagger/swagger-ui-bundle.js.LICENSE.txt" \
   "$swagger/swagger-ui.css" "$swagger/favicon-32x32.png" "$dest/"
cp "$swagger/LICENSE" "$dest/LICENSE-swagger-ui.txt"
cp "$swagger/NOTICE" "$dest/NOTICE-swagger-ui.txt"
cp "$redoc/bundles/redoc.standalone.js" "$redoc/bundles/redoc.standalone.js.LICENSE.txt" "$dest/"
cp "$redoc/LICENSE" "$dest/LICENSE-redoc.txt"

{
  echo "# Self-hosted API documentation assets"
  echo
  echo "Served by \`backend/app/main.py\` at \`/docs/static/\` so \`/docs\` (Swagger UI) and"
  echo "\`/redoc\` (Redoc) work without an internet connection. Byte-identical copies"
  echo "of published npm packages. Do not edit; regenerate with"
  echo "\`scripts/vendor_api_docs.sh\`. The backend serves \`redoc.standalone.js\` with"
  echo "one change, made in memory: the CDN address of the logo in Redoc's footer is"
  echo "emptied (\`REDOC_CDN_LOGO\` in \`backend/app/main.py\`)."
  echo
  echo "| Package | Version | License |"
  echo "|---|---|---|"
  echo "| [swagger-ui-dist](https://www.npmjs.com/package/swagger-ui-dist) | ${SWAGGER_UI_VERSION} | Apache-2.0 (\`LICENSE-swagger-ui.txt\`, \`NOTICE-swagger-ui.txt\`; bundled third-party notices in \`swagger-ui-bundle.js.LICENSE.txt\`) |"
  echo "| [redoc](https://www.npmjs.com/package/redoc) | ${REDOC_VERSION} | MIT (\`LICENSE-redoc.txt\`; bundled third-party notices in \`redoc.standalone.js.LICENSE.txt\`) |"
  echo
  echo "SHA-256:"
  echo
  echo '```text'
  (cd "$dest" && sha256sum favicon-32x32.png redoc.standalone.js swagger-ui-bundle.js swagger-ui.css)
  echo '```'
} > "$dest/README.md"

echo "Vendored swagger-ui-dist ${SWAGGER_UI_VERSION} and redoc ${REDOC_VERSION} into ${dest}/"
