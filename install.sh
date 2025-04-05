#!/usr/bin/env bash
set -e

REPO="yniverz/WayPointDB-AirTag-Integration"
APP_NAME="WayPointDB.AirTags.app"
ZIP_NAME="${APP_NAME}.zip"
INSTALL_PATH="/Applications"

echo "Fetching the latest release download URL from GitHub..."
DOWNLOAD_URL=$(
  curl -s https://api.github.com/repos/${REPO}/releases/latest \
  | grep "browser_download_url" \
  | grep "${ZIP_NAME}" \
  | cut -d '"' -f 4
)

if [[ -z "${DOWNLOAD_URL}" ]]; then
  echo "Error: Could not find a download URL for '${ZIP_NAME}'."
  exit 1
fi

echo "Found download URL: ${DOWNLOAD_URL}"
echo "Downloading ${ZIP_NAME}..."
curl -L -o "/tmp/${ZIP_NAME}" "${DOWNLOAD_URL}"

echo "Unzipping into ${INSTALL_PATH}..."
unzip -o "/tmp/${ZIP_NAME}" -d "${INSTALL_PATH}"

# Remove extended attributes (quarantine, etc.)
echo "Removing extended attributes from ${APP_NAME}..."
xattr -cr "${INSTALL_PATH}/${APP_NAME}"

# Add to login items via AppleScript
echo "Adding ${APP_NAME} to login items..."
osascript <<EOF
tell application "System Events"
    make new login item at end with properties { \
       path:"${INSTALL_PATH}/${APP_NAME}", \
       hidden:false \
    }
end tell
EOF

# Attempting to manage Full Disk Access is not straightforward
# This step often requires manual user interaction or an MDM (managed device) profile.
echo
echo "-------------------------"
echo " Full Disk Access Notice "
echo "-------------------------"
echo "macOS does not allow scripts to automatically grant Full Disk Access."
echo "Please open 'System Settings' > 'Privacy & Security' > 'Full Disk Access'"
echo "and manually add '${APP_NAME}' if required."
echo

echo "Installation complete!"
exit 0