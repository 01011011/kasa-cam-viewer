"""
StreamReader – v2 (quality via .env)
====================================
• curl --raw  →  ffmpeg → MJPEG (preview) → browser queue
• curl --raw  →  ffmpeg → x264 rotating segments → disk

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

        # ——— preview parameters (env can override defaults) ———
        self.name   = name
        self.url    = f"https://{ip}:19443/https/stream/mixed?video=h264"
        self.auth   = f"{user}:{pwd}"

        self.fps    = int(os.getenv("FPS", fps))
        self.width  = int(os.getenv("WIDTH", width))  # 0 = no scaling
        self.mjpg_q = int(os.getenv("MJPEG_Q", 4))    # JPEG quality

        # ——— recording / retention ————————————————
        self.seg_secs = int(os.getenv("SEG_SECS", seg_secs))
        self.wrap     = int(os.getenv("WRAP_FILES", 2))
        self.rec_dir  = Path(os.getenv("RECORD_DIR", record_dir))
        self.rec_dir.mkdir(exist_ok=True, parents=True)

        self.crf     = os.getenv("CRF", "28")
        self.preset  = os.getenv("PRESET", "veryfast")

        # ——— frame queue for MJPEG (≈ 6 s max @ 10 fps) ———
        self.q = queue.Queue(maxsize=60)

    # ======================================================================
    def start(self):
        curl_cmd = [
            CURL, "-k", "--raw", "--no-buffer",
            "-H", "Range: bytes=0-",
            "-u", self.auth, self.url, "--output", "-" ]

        curl_proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE)

        out_pat = self.rec_dir / f"{self.name}_%02d.mp4"

        scale_filter = f",scale={self.width}:-1" if self.width else ""
        ff_cmd = [
            FFMPEG, "-loglevel", "error",
            "-f", "h264", "-i", "pipe:0",

            # ——— split: preview branch & recording branch ———
            "-filter_complex",
            (f"[0:v]split=2[pv][pr];"
             f"[pv]fps={self.fps}{scale_filter},"
             f"format=yuvj422p[mjpeg]"),

            # —— branch 1 – MJPEG to stdout ————————————
            "-map", "[mjpeg]", "-c:v", "mjpeg",
                   "-q:v", str(self.mjpg_q),
            "-f",  "mjpeg",  "pipe:1",

            # —— branch 2 – x264 segments to disk —————————
            "-map", "[pr]", "-c:v", "libx264",
                   "-preset", self.preset,
                   "-crf",    self.crf,
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
        SOI, EOI = b"\xff\xd8", b"\xff\xd9"   # start/end JPEG markers
        while True:
            chunk = stdout.read(8192)
            if not chunk:
                break
            buf += chunk
            while True:
                s = buf.find(SOI); e = buf.find(EOI)
                if s != -1 and e != -1 and e > s:
                    if not self.q.full():
                        self.q.put(buf[s:e+2])
                    buf = buf[e+2:]
                else:
                    break
