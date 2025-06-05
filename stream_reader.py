"""
StreamReader – v2 (quality via .env)
====================================
• curl --raw  →  ffmpeg → MJPEG (preview) → browser queue
• curl --raw  →  ffmpeg → x264 rotating segments → disk

Only WRAP_FILES MP4s are kept (default 2).
"""

import os, sys, queue, threading, subprocess, shutil, time
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

        self.last_frame_time = time.time()
        self._stop_event = threading.Event()
        self._proc_lock = threading.Lock()
        self._ff_proc = None
        self._curl_proc = None
        self._watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)

    # ======================================================================
    def start(self):
        self._stop_event.clear()
        self._start_pipeline()
        self._watchdog_thread.start()

    def stop(self):
        self._stop_event.set()
        with self._proc_lock:
            if self._ff_proc:
                self._ff_proc.kill()
            if self._curl_proc:
                self._curl_proc.kill()

    def _start_pipeline(self):
        with self._proc_lock:
            # Start curl
            curl_cmd = [
                CURL, "-k", "--raw", "--no-buffer",
                "-H", "Range: bytes=0-",
                "-u", self.auth, self.url, "--output", "-" 
            ]
            self._curl_proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE)

            out_pat = self.rec_dir / f"{self.name}_%02d.mp4"            # Working filter complex with timestamp using Windows font
            font_path = "C\\:/Windows/Fonts/arial.ttf"  # Windows system font path for ffmpeg
            timestamp_text = f"drawtext=fontfile='{font_path}':text='%{{localtime}}':x=10:y=10:fontsize=24:fontcolor=white"
            
            if self.width:
                filter_complex = (
                    f"[0:v]split=2[pv][pr];"
                    f"[pv]fps={self.fps},scale={self.width}:-1,{timestamp_text},format=yuvj422p[mjpeg];"
                    f"[pr]scale={self.width}:-1,{timestamp_text}[pr_out]"
                )
            else:
                filter_complex = (
                    f"[0:v]split=2[pv][pr];"
                    f"[pv]fps={self.fps},{timestamp_text},format=yuvj422p[mjpeg];"
                    f"[pr]{timestamp_text}[pr_out]"
                )
            print(f"[DEBUG] ffmpeg filter_complex: {filter_complex}")
            ff_cmd = [
                FFMPEG, "-loglevel", "error",
                "-fflags", "+discardcorrupt",
                "-flags", "low_delay",
                "-analyzeduration", "1000000",
                "-probesize", "1000000",
                "-err_detect", "ignore_err",
                "-f", "h264", "-i", "pipe:0",
                "-filter_complex", filter_complex,
                # MJPEG preview branch
                "-map", "[mjpeg]", "-c:v", "mjpeg",
                "-q:v", str(self.mjpg_q),
                "-f",  "mjpeg",  "pipe:1",
                # Recording branch without timestamp for now
                "-map", "[pr_out]", "-c:v", "libx264",
                "-preset", self.preset,
                "-crf",    self.crf,
                "-movflags", "+faststart",
                "-f",  "segment",
                "-segment_time",   str(self.seg_secs),
                "-segment_wrap",   str(self.wrap),
                "-reset_timestamps", "1",
                str(out_pat)
            ]
            self._ff_proc = subprocess.Popen(ff_cmd,
                                             stdin=self._curl_proc.stdout,
                                             stdout=subprocess.PIPE)
            threading.Thread(target=self._extract_jpeg,
                             args=(self._ff_proc.stdout,), daemon=True).start()

    def _restart_pipeline(self):
        print(f"[{self.name}] Restarting ffmpeg/curl pipeline...")
        self.stop()
        time.sleep(1)
        self._start_pipeline()

    def _watchdog(self):
        while not self._stop_event.is_set():
            time.sleep(2)
            # If ffmpeg or curl has exited, restart
            with self._proc_lock:
                ff_dead = self._ff_proc and (self._ff_proc.poll() is not None)
                curl_dead = self._curl_proc and (self._curl_proc.poll() is not None)
            if ff_dead or curl_dead:
                print(f"[{self.name}] ffmpeg or curl exited unexpectedly.")
                self._restart_pipeline()
                continue
            # If no frame for 10 seconds, restart
            if time.time() - self.last_frame_time > 10:
                print(f"[{self.name}] No frames received for 10s. Restarting pipeline.")
                self._restart_pipeline()

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
            try:
                chunk = stdout.read(8192)
                if not chunk:
                    break
                buf += chunk
                while True:
                    s = buf.find(SOI); e = buf.find(EOI)
                    if s != -1 and e != -1 and e > s:
                        if not self.q.full():
                            self.q.put(buf[s:e+2])
                        self.last_frame_time = time.time()
                        buf = buf[e+2:]
                    else:
                        break
            except Exception as ex:
                print(f"[{self.name}] JPEG extraction error: {ex}")
                break
        # If we exit the loop, trigger a restart
        self._restart_pipeline()
