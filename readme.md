# 3rdiSlideshow

An app for streaming all the 3rdi Images to the video output, fullscreen, time-synchronized with the originals.

## Setup

Hardware: [MeLE Quieter3Q Fanless Mini PC](https://www.amazon.com/MeLE-Quieter3Q-Portable-Ethernet-Industrial/dp/B09XB5SPJT)

1. Install [Ubuntu 22.04 for Desktop](https://releases.ubuntu.com/jammy/). For this to work correctly, I had to create the bootable USB stick on Windows instead of MacOS. Then press F7 or Delete to enter boot menu and select the USB for boot.
2. Enable Remote Desktop in Settings.
3. Disable the keyring by [setting the password to empty](https://askubuntu.com/a/875). Then reboot and check that screen sharing works correctly (test using Microsoft Remote Desktop app).
4. 

```
sudo apt install -y git python3-pip python3.10-venv openssh-server
mkdir -m700 ~/.ssh
wget -qO- https://github.com/<username>.keys | head -n1 > ~/.ssh/authorized_keys # Replace <username> with your GitHub username
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ln -s ~/Documents/3rdiStream images
```