# Overview

**NOTE: Windows only!! If you are on mac, you will need to install python to run the script.**

There are 2 parts to this:
1. A chrome / firefox extension to read your authentication token from momen
2. An exe file which you pass in your token and username to download the files

# Instructions

1. Go to releases https://github.com/honeyedoasis/momen/releases
2. Download `momen-windows.exe` and `Source code (zip)`
3. Unzip the source code and move the `.exe` into the folder 

## 1. Getting your token

### For chrome
1. Navigate to `chrome://extensions`
2. Click `Load unpacked` in the top left and select the `extensions` folder

### For firefox
1. Navigate to `about:debugging#/runtime/this-firefox`
2. Click `Load Temporary Add-on...` and select `extension/manifest.json`

### Using the extension

1. Navigate to `momen****.com` homepage
2. Click the extension button in the top right (looks like a puzzle piece)
3. Click the token grabber extension 
4. Copy your token

**NOTE:** The token only lasts for 1 day!

## 2. Settings

Choose the artist to download, set your token and username. 

Edit the plugin `config.json`. There are 3 fields here:

* `Token:` The token from using the extension
* `Username:` Your username. Can be found by going to `https://momen****.com/en/collection` and it will show `https://momen****.com/en/collection/YOUR_USERNAME`.
* `Artist:` The name of the artist `https://momen****.com/en/artist/fromis_9`

## 3. Downloading the media
1. Run `momen-windows.exe`
2. It will download to the subfolder `/momen****`