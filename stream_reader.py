"""
StreamReader
============
■ curl --raw                → ffmpeg → MJPEG  → browser
■ curl --raw (second pipe)  → ffmpeg → x264 segments → disk

Only WRAP_FILES MP4s are kept (default 2).
"""

import os, sys, queue, threading, subprocess, shutil
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

CURL   = shutil.which("curl")   or sys.exit("❌  curl.exe not on PATH")
FFMPEG = shutil.which("ffmpeg") or sys.exit("❌  ffmpeg.exe not on PATH")


class StreamReader:
    def __init__(self, name, ip, user, pwd,
                 fps=10, width=640,
                 seg_secs=10, record_dir="recordings"):

        # ─── preview parameters ────────────────────────────────────────────
        self.name  = name
        self.url   = f"https://{ip}:19443/https/stream/mixed?video=h264"
        self.auth  = f"{user}:{pwd}"
        self.fps   = int(os.getenv("FPS",   fps))
        self.width = int(os.getenv("WIDTH", width))

        # ─── recording / retention ────────────────────────────────────────
        self.seg_secs = int(os.getenv("SEG_SECS", seg_secs))
        self.wrap     = int(os.getenv("WRAP_FILES", 2))
        self.rec_dir  = Path(os.getenv("RECORD_DIR", record_dir))
        self.rec_dir.mkdir(exist_ok=True, parents=True)

        # —— frame queue for MJPEG —— (max ≈ 6 s @ 10 fps) ————————
        self.q = queue.Queue(maxsize=60)

    # ======================================================================
    def start(self):
        curl_cmd = [
            CURL, "-k", "--raw", "--no-buffer",
            "-H", "Range: bytes=0-",
            "-u", self.auth, self.url, "--output", "-" ]

        curl_proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE)

        out_pat = self.rec_dir / f"{self.name}_%02d.mp4"

        ff_cmd = [
            FFMPEG, "-loglevel", "error",
            "-f", "h264", "-i", "pipe:0",

            # ─── split to MJPEG + recorder ───────────────────────────────
            "-filter_complex",
            (f"[0:v]split=2[pv][pr];"
             f"[pv]fps={self.fps},scale={self.width}:-1,"
             f"format=yuvj422p[mjpeg]"),

            # —— branch 1 : preview to stdout ————————————————
            "-map", "[mjpeg]", "-c:v", "mjpeg", "-q:v", "4",
            "-f",  "mjpeg",  "pipe:1",

            # —— branch 2 : x264 segments to disk ——————————————
            "-map", "[pr]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-movflags", "+faststart",
            "-f",  "segment",
            "-segment_time",   str(self.seg_secs),
            "-segment_wrap",   str(self.wrap),
            "-reset_timestamps", "1",
            str(out_pat)
        ]

        ff = subprocess.Popen(ff_cmd,
                              stdin=curl_proc.stdout,
                              stdout=subprocess.PIPE)

        threading.Thread(target=self._extract_jpeg,
                         args=(ff.stdout,), daemon=True).start()

    # ======================================================================
    def frame_generator(self):
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            yield boundary + self.q.get() + b"\r\n"

    # ---------------------------------------------------------------------
    def _extract_jpeg(self, stdout):
        buf = b""
        while True:
            chunk = stdout.read(8192)
            if not chunk:
                break
            buf += chunk
            while True:
                s = buf.find(b"\xff\xd8"); e = buf.find(b"\xff\xd9")
                if s != -1 and e != -1 and e > s:
                    if not self.q.full():
                        self.q.put(buf[s:e+2])
                    buf = buf[e+2:]
                else:
                    break
