# KASA Camera Viewer

A robust web-based application for streaming and recording video from **KASA Spot Pan Tilt cameras** with timestamp overlays. This application eliminates the need for cloud subscriptions while providing local control over your camera feeds and recordings.

## ✨ Features

- **🎥 Live Streaming**: Real-time video streams from multiple KASA cameras via web interface
- **⏰ Timestamp Overlays**: Automatic timestamp display on both live streams and recordings
- **📹 Local Recording**: Continuous recording with automatic file rotation and retention
- **🔄 Auto-Recovery**: Automatic restart on connection failures with watchdog monitoring
- **🎛️ Quality Control**: Configurable video quality, frame rate, and encoding settings
- **🌐 Web Interface**: Clean, responsive web UI for viewing multiple camera feeds
- **🐳 Docker Support**: Easy deployment with Docker containerization
- **🔒 Privacy-Focused**: No cloud dependencies - all data stays local

## 🏗️ Architecture

The application uses a robust streaming pipeline:
```
KASA Camera → curl (HTTPS) → ffmpeg (H.264 decode) → Split Stream
                                    ↓                    ↓
                            MJPEG (web preview)    MP4 (recording)
                                    ↓                    ↓
                              Flask Server         Local Storage
```

## 📋 Requirements

- **Hardware**: KASA Spot Pan Tilt Camera(s)
- **Software**: Python 3.12+, ffmpeg, curl
- **Network**: Cameras on local network with HTTPS access
- **Storage**: Local disk space for recordings

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd cam-view
```

### 2. Setup Environment
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your camera credentials
notepad .env  # Windows
# or
nano .env     # Linux/Mac
```

### 3. Configure Cameras
Edit `.env` file with your camera details:
```env
# Camera 1 Settings
CAM1_IP=192.168.1.100
CAM1_USER=your_camera_username
CAM1_PASS=your_camera_password

# Camera 2 Settings  
CAM2_IP=192.168.1.101
CAM2_USER=your_camera_username
CAM2_PASS=your_camera_password

# Recording Settings
SEG_SECS=3600          # 1 hour segments
WRAP_FILES=12          # Keep 12 hours of recordings
RECORD_DIR=recordings

# Video Quality
WIDTH=1280             # HD resolution
FPS=15                 # Frame rate
CRF=24                 # Video quality (lower = better)
```

### 4. Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac

# Install requirements
pip install -r requirements.txt
```

### 5. Run Application
```bash
python app.py
```

Visit `http://localhost:5000` to view your camera feeds!

## 🐳 Docker Deployment

### Build and Run
```bash
# Build image
docker build -t kasa-cam-viewer .

# Run container
docker run -d \
  --name kasa-cameras \
  -p 5000:5000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/recordings:/app/recordings \
  kasa-cam-viewer
```

### Docker Compose
```yaml
version: '3.8'
services:
  kasa-cam-viewer:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./.env:/app/.env
      - ./recordings:/app/recordings
    restart: unless-stopped
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAM1_IP` | - | Camera 1 IP address |
| `CAM1_USER` | - | Camera 1 username |
| `CAM1_PASS` | - | Camera 1 password |
| `CAM2_IP` | - | Camera 2 IP address |
| `CAM2_USER` | - | Camera 2 username |
| `CAM2_PASS` | - | Camera 2 password |
| `SEG_SECS` | 3600 | Recording segment duration (seconds) |
| `WRAP_FILES` | 12 | Number of recording files to keep |
| `RECORD_DIR` | recordings | Recording directory |
| `WIDTH` | 1280 | Video width (0 = original) |
| `FPS` | 15 | Preview frame rate |
| `MJPEG_Q` | 2 | MJPEG quality (1-31, lower = better) |
| `CRF` | 24 | H.264 quality (18-28, lower = better) |
| `PRESET` | fast | Encoding speed (fast, medium, slow) |

### Recording Management

- **Automatic Rotation**: Old recordings are automatically deleted when `WRAP_FILES` limit is reached
- **Segment Duration**: Configure with `SEG_SECS` (default: 1 hour)
- **Storage Location**: Set with `RECORD_DIR` (default: `recordings/`)

## 🔧 Troubleshooting

### Common Issues

**No video display:**
- Check camera IP addresses and credentials in `.env`
- Verify cameras are accessible on local network
- Check ffmpeg and curl are installed and in PATH

**Application crashes:**
- Check logs for ffmpeg errors
- Verify camera HTTPS certificates (app uses `-k` flag for self-signed certs)
- Ensure sufficient disk space for recordings

**Performance issues:**
- Adjust `FPS` and `WIDTH` settings for lower bandwidth
- Increase `CRF` value for smaller file sizes
- Use faster `PRESET` values for lower CPU usage

### Logs and Debugging

The application provides detailed logging:
- ffmpeg filter pipeline details
- Connection status and restart events
- Recording file creation and rotation

## 🛠️ Development

### Architecture Details

- **StreamReader Class**: Manages individual camera streams with automatic recovery
- **Flask Server**: Serves web interface and MJPEG streams
- **FFmpeg Pipeline**: Handles H.264 decoding, timestamp overlay, and dual output
- **Watchdog Timer**: Monitors process health and triggers restarts

### Key Features

- **Robust Error Handling**: Automatic restart on ffmpeg/curl failures
- **Memory Management**: Bounded frame queues prevent memory leaks
- **Process Monitoring**: Watchdog threads monitor subprocess health
- **Clean Shutdown**: Proper resource cleanup on application exit

## 📁 Project Structure

```
cam-view/
├── app.py                 # Flask web server
├── stream_reader.py       # Core streaming and recording logic
├── templates/
│   └── index.html        # Web interface template
├── recordings/           # Video recordings (auto-created)
├── .env.template         # Configuration template
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
└── README.md           # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **KASA/TP-Link** for the camera hardware
- **FFmpeg** for video processing capabilities
- **Flask** for the lightweight web framework

