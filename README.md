# Kasa Cam Viewer

Kasa Cam Viewer is a lightweight application designed to stream video from the **KASA Spot Pan Tilt Camera** and save recordings locally. This eliminates the need for cloud subscriptions, giving users full control over their recordings and privacy.

## Features
- **Live Streaming**: View real-time video streams from your KASA Spot Pan Tilt Camera.
- **Local Recording**: Save video recordings directly to your local storage.
- **Cloud-Free**: No reliance on cloud subscriptions for video storage or streaming.
- **Privacy-Focused**: Keep your recordings secure and private on your own devices.

## Requirements
- A KASA Spot Pan Tilt Camera.
- Python 3.8+.
- Necessary dependencies (see `requirements.txt`).

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/01011011/kasa-cam-viewer.git
   cd kasa-cam-viewer

2. Create a .env file in the root directory with the following format:

# .env file for Kasa Cam Viewer

# Kasa Camera IP Address
CAMERA_IP=192.168.1.100

# Kasa Camera Username
CAMERA_USERNAME=your_username

# Kasa Camera Password
CAMERA_PASSWORD=your_password

# Recording Directory (default: recordings/)
RECORDING_DIR=recordings/

3. Install dependencies

pip install -r requirements.txt

4. Run the application:

python stream_reader.py

Notes
Ensure the .env file is configured with the necessary credentials for your camera.
Recordings are saved in the recordings/ folder by default.
License
This project is licensed under the MIT License.
