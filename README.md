[![License: NCPUL](https://img.shields.io/badge/license-NCPUL-blue.svg)](./LICENSE.md)

# WayPointDB-AirTag-Integration
Lightweight App to integrate AirTags into WayPointDB

<img width="830" alt="Preview" src="https://github.com/user-attachments/assets/6a898ac1-19c9-41a2-a243-e676f86c64ef" />

# Prerequisites
- A Device running MacOS at all times
- Sign into your iCloud account on the Mac User you want to use for AirTags
- Ensure FindMy is enabled in the iCloud settings on the Mac User
- Ensure Location Services is enabled on the Mac User
- Ensure you have a supported MacOS version (11.13-14.3.1)

# Installation
Run the following command to install the script:

```bash
curl -sSL https://raw.githubusercontent.com/yniverz/WayPointDB-AirTag-Integration/refs/heads/main/install.sh | bash
```

- Before being able to use this, upon opening macos might flag this as insecure. You need to go to your System Settings, `Privacy & Security`and find and click the `Open Anyway`option.
- Activate `Full Disk Access` for the app (you will need to run it first, so it shows up in the settings)
- Run the Application (Updates will be sent while app is running)
- Enjoy

# Update
Run the following command to update the script:

```bash
curl -sSL https://raw.githubusercontent.com/yniverz/WayPointDB-AirTag-Integration/refs/heads/main/update.sh | bash
```

# Build Yourself (Only possible on MacOS)
- Clone this repository
- Install pip packages: `py2app`, `requests`, (`tkinter` should be preinstalled with python)
- Navigate to the repo directory
- Run `python setup.py py2app` and wait a little while
- Find the `.app` file in the newly created `dist` folder


### References
- Icon made by [Freepik](https://www.flaticon.com/authors/freepik)
