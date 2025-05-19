import os, time
from flask import Flask, Response, render_template
from dotenv import load_dotenv
from stream_reader import StreamReader
from pathlib import Path
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path, override=True)

app = Flask(__name__)

# ─── set up the two camera streams ─────────────────────────────────────────
streams = []

cam_def = [
    ("cam1", os.getenv("CAM1_IP"), os.getenv("CAM1_USER"), os.getenv("CAM1_PASS")),
    ("cam2", os.getenv("CAM2_IP"), os.getenv("CAM2_USER"), os.getenv("CAM2_PASS"))
]

for name, ip, user, pwd in cam_def:
    if ip and user and pwd:
        s = StreamReader(name, ip, user, pwd)
        s.start()
        streams.append(s)
        time.sleep(0.3)   # tiny stagger so curl TLS doesn’t collide

# ─── Flask routes ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", cameras=[s.name for s in streams])

@app.route("/video/<cam>")
def video(cam):
    # find the requested stream
    sr = next((s for s in streams if s.name == cam), None)
    if sr is None:
        return "camera not found", 404
    return Response(sr.frame_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# ─── run ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
