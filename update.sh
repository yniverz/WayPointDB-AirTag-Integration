#!/usr/bin/env bash
set -e

###############################################################################
# Configuration
###############################################################################

REPO="yniverz/WayPointDB-AirTag-Integration"
APP_NAME="WayPointDB.AirTags.app"
ZIP_NAME="${APP_NAME}.zip"
INSTALL_PATH="/Applications"

# Files (relative to .app) you want to preserve and restore
CONFIG_FILES=(
  "Contents/Resources/waypointdb_findmy_config.json"
  "Contents/Resources/pending_data.json"
)

TMP_DIR="/tmp/waypointdb_airtags_update"

###############################################################################
# Fetch Latest Release
###############################################################################

echo "Fetching the latest release download URL from GitHub..."
DOWNLOAD_URL=$(
  curl -s "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep "browser_download_url" \
  | grep "${ZIP_NAME}" \
  | cut -d '"' -f 4
)

if [[ -z "${DOWNLOAD_URL}" ]]; then
  echo "Error: Could not find a download URL for '${ZIP_NAME}'."
  exit 1
fi

echo "Found download URL: ${DOWNLOAD_URL}"
echo "Downloading ${ZIP_NAME} to /tmp..."
curl -L -o "/tmp/${ZIP_NAME}" "${DOWNLOAD_URL}"

###############################################################################
# Unzip into Temporary Directory
###############################################################################

echo "Unzipping into ${TMP_DIR}..."
rm -rf "${TMP_DIR}"
mkdir -p "${TMP_DIR}"
unzip -o "/tmp/${ZIP_NAME}" -d "${TMP_DIR}"

NEW_APP_PATH="${TMP_DIR}/${APP_NAME}"
OLD_APP_PATH="${INSTALL_PATH}/${APP_NAME}"

if [[ ! -d "${NEW_APP_PATH}" ]]; then
  echo "Error: The unzipped application folder was not found at ${NEW_APP_PATH}."
  exit 1
fi

###############################################################################
# Backup Config/JSON Files from Existing App
###############################################################################

echo "Backing up your existing config/persistence files..."
BACKUP_DIR="${TMP_DIR}/backup"
mkdir -p "${BACKUP_DIR}"

for cfg in "${CONFIG_FILES[@]}"; do
  SRC_CFG="${OLD_APP_PATH}/${cfg}"
  if [[ -f "${SRC_CFG}" ]]; then
    DEST_CFG_DIR="$(dirname "${BACKUP_DIR}/${cfg}")"
    mkdir -p "${DEST_CFG_DIR}"
    echo "  - Backing up ${cfg}"
    cp "${SRC_CFG}" "${BACKUP_DIR}/${cfg}"
  fi
done

###############################################################################
# Remove Old App and Move in New One
###############################################################################

echo "Removing old app at ${OLD_APP_PATH}..."
rm -rf "${OLD_APP_PATH}"

echo "Placing new app into ${INSTALL_PATH}..."
mv "${NEW_APP_PATH}" "${INSTALL_PATH}"

###############################################################################
# Restore Backed-Up Files
###############################################################################

echo "Restoring config/persistence files..."
for cfg in "${CONFIG_FILES[@]}"; do
  BK_CFG="${BACKUP_DIR}/${cfg}"
  NEW_CFG_PATH="${OLD_APP_PATH}/${cfg}"
  
  if [[ -f "${BK_CFG}" ]]; then
    echo "  - Restoring ${cfg}"
    # Make sure the target directory exists
    mkdir -p "$(dirname "${NEW_CFG_PATH}")"
    cp "${BK_CFG}" "${NEW_CFG_PATH}"
  fi
done

###############################################################################
# Clean Up and Finalize
###############################################################################

echo "Clearing extended attributes from ${OLD_APP_PATH}..."
xattr -cr "${OLD_APP_PATH}" || true

echo "Update complete!"
exit 0