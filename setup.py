from setuptools import setup
import os
import shutil

TEMP_DIR = 'temp'
PACKAGE_FILES = [
    'AirTag-grabber.py',
    'favicon.png',
]

APP = ['temp/AirTag-grabber.py']
OPTIONS = {
    'iconfile': 'temp/favicon.png', 
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True   # or 'NSUIElement': True to run without a full Dock icon,
    },
}


if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
for file in PACKAGE_FILES:
    shutil.copy(file, TEMP_DIR)

# replace line that looks like "VERSION = "---" APP file with the version of your app found in the VERSION file
with open('VERSION', 'r') as version_file:
    version = version_file.read().strip()
    OPTIONS['plist']['CFBundleShortVersionString'] = version
    OPTIONS['plist']['CFBundleVersion'] = version

# go through each line of app file
with open(APP[0], 'r') as app_file:
    lines = app_file.readlines()
    for i, line in enumerate(lines):
        if line.startswith('VERSION ='):
            lines[i] = f'VERSION = "{version}"\n'
            break
    # write the modified lines back to the file
with open(APP[0], 'w') as app_file:
    app_file.writelines(lines)



setup(
    app=APP,
    name='WayPointDB AirTags',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)