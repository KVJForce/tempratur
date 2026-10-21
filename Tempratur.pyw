"""Tempratur - internal temperature monitor for Windows.

GPU temperatures come from nvidia-smi. CPU temperature comes from the
Windows thermal-zone performance counter, which is readable without
admin on most laptops; the ACPI WMI class is the fallback when that
counter is missing. The footer buttons load all CPU cores or the NVIDIA
GPU for 45 seconds.

Run:     python Tempratur.pyw
Check:   python Tempratur.pyw --selftest
Closing the window keeps the monitor in the notification area.
"""

import atexit
import base64
import ctypes
import math
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import traceback
import winreg
import zlib
from collections import deque
from io import BytesIO

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pystray
    from PIL import Image
except Exception:
    pystray = None
    Image = None

ICON_PNG = (
    "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"
)

# ---------------------------------------------------------------- palette ---

BG = "#0A0D13"
CARD = "#111722"
CARD_HOVER = "#151D2A"
BORDER = "#1E2836"
TEXT = "#E7EDF6"
MUTED = "#8B97A8"
DIM = "#6F7B8D"
TRACK = "#1B2433"
COOL = "#3DDC97"
WARM = "#FFB454"
HOT = "#FF5B5B"
CPU_BLUE = "#5AA9FF"
MEM_PURPLE = "#B08CFF"

FAM = "Segoe UI"
SEMI = "Segoe UI Semibold"
NO_WINDOW = 0x08000000

DPI = 96


def s(n):
    """Scale a design pixel to the current display DPI."""
    return max(1, int(round(n * DPI / 96)))


_fonts = {}


def fnt(size, semi=False):
    key = (size, semi)
    if key not in _fonts:
        _fonts[key] = tkfont.Font(family=SEMI if semi else FAM, size=-s(size))
    return _fonts[key]


def enable_dpi():
    global DPI
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    try:
        DPI = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        DPI = 96


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def temp_color(v):
    return COOL if v < 60 else WARM if v < 80 else HOT


def state_word(v):
    return "cool" if v < 60 else "warm" if v < 80 else "hot"


def gauge_frac(v, scale):
    lo, hi = scale
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def num(line):
    try:
        return float(str(line).strip().split(",")[0])
    except (ValueError, IndexError):
        return None


def parse_temp(line):
    v = num(line)
    return v if v is not None and 5 <= v <= 115 else None


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def first_instance():
    """False when another copy is already running."""
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        # the handle stays open for the life of the process, which holds the lock
        k32.CreateMutexW(None, False, "Local\\TempraturMonitor")
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                None, "Tempratur is already running. Check the taskbar or the "
                      "notification area.",
                "Tempratur", 0x40)
            return False
        return True
    except Exception:
        return True


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Tempratur"


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    exe = sys.executable
    if not exe.lower().endswith("pythonw.exe"):
        quiet = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(quiet):
            exe = quiet
    return f'"{exe}" "{os.path.abspath(__file__)}" --tray'


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
        return True
    except OSError:
        return False


def set_autostart(on):
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if on:
                winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def rrect(c, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = (x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1)
    return c.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------- sensors ---

PS_ONE = r"""
$ErrorActionPreference = 'SilentlyContinue'
$z = Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation
if ($z) {
  $t = $z | Sort-Object HighPrecisionTemperature -Descending | Select-Object -First 1
  if ($t -and $t.HighPrecisionTemperature -gt 0) {
    [math]::Round(($t.HighPrecisionTemperature / 10) - 273.15, 1)
    exit
  }
  if ($t -and $t.Temperature -gt 0) {
    [math]::Round($t.Temperature - 273.15, 1)
    exit
  }
}
try {
  $a = Get-CimInstance -Namespace root/WMI -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop
  if (-not $a) { 'none'; exit }
  $t = $a | Sort-Object CurrentTemperature -Descending | Select-Object -First 1
  [math]::Round(($t.CurrentTemperature / 10) - 273.15, 1)
} catch { 'denied' }
"""

PS_STREAM = r"""
$ErrorActionPreference = 'SilentlyContinue'
while ($true) {
  $v = 'none'
  $z = Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation
  if ($z) {
    $t = $z | Sort-Object HighPrecisionTemperature -Descending | Select-Object -First 1
    if ($t -and $t.HighPrecisionTemperature -gt 0) {
      $v = [math]::Round(($t.HighPrecisionTemperature / 10) - 273.15, 1)
    } elseif ($t -and $t.Temperature -gt 0) {
      $v = [math]::Round($t.Temperature - 273.15, 1)
    }
  }
  if ($v -eq 'none') {
    try {
      $a = Get-CimInstance -Namespace root/WMI -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop
      if ($a) {
        $t = $a | Sort-Object CurrentTemperature -Descending | Select-Object -First 1
        $v = [math]::Round(($t.CurrentTemperature / 10) - 273.15, 1)
      }
    } catch { $v = 'denied' }
  }
  [Console]::Out.WriteLine($v)
  [Console]::Out.Flush()
  Start-Sleep -Milliseconds 2000
}
"""

GPU_CMD = ["nvidia-smi", "-lms", "2000", "--query-gpu=temperature.gpu",
           "--format=csv,noheader"]

def ps_cmd(script):
    enc = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc]


def _pump(proc, q):
    for line in proc.stdout:
        q.put(line)
    q.put(None)


class Sensors:
    def __init__(self):
        self.cpu = None
        self.gpu = None
        self.cpu_t = 0.0
        self.gpu_t = 0.0
        self.cpu_lock = None          # None -> probing, live / denied / none
        self.gpu_seen = False
        self.gpu_name = "GPU"
        self.lo = {}
        self.hi = {}
        self.cpu_hist = deque()
        self.gpu_hist = deque()
        self._procs = []
        self._running = True
        atexit.register(self.stop)

    def start(self):
        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        # GPU: ask for the card name once, then keep a stream open.
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=8,
                                 creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
            name = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
            if name:
                self.gpu_name = name
                self.gpu_seen = True
                threading.Thread(target=self._stream, args=(GPU_CMD, self._gpu_line),
                                 daemon=True).start()
        except Exception:
            pass

        # CPU: one probe decides whether a stream is worth keeping.
        try:
            out = subprocess.run(ps_cmd(PS_ONE), capture_output=True, text=True, timeout=20,
                                 creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
            last = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
            v = parse_temp(last)
            if v is not None:
                self._set("cpu", v)
                self.cpu_lock = "live"
                threading.Thread(target=self._stream, args=(ps_cmd(PS_STREAM), self._cpu_line),
                                 daemon=True).start()
            elif "denied" in last.lower():
                self.cpu_lock = "denied"
            else:
                self.cpu_lock = "none"
        except Exception:
            self.cpu_lock = "none"

    def _cpu_line(self, line):
        v = parse_temp(line)
        if v is not None:
            self.cpu_lock = "live"
            self._set("cpu", v)
        elif "denied" in line.lower():
            self.cpu_lock = "denied"

    def _gpu_line(self, line):
        v = num(line)
        if v is not None and 0 <= v <= 120:
            self._set("gpu", v)

    def _set(self, key, v):
        if key == "cpu":
            self.cpu = v
            self.cpu_t = time.time()
        else:
            self.gpu = v
            self.gpu_t = time.time()
        self.lo[key] = min(self.lo.get(key, v), v)
        self.hi[key] = max(self.hi.get(key, v), v)

    def prune(self, now):
        for hist in (self.cpu_hist, self.gpu_hist):
            while hist and hist[0][0] < now - 180:
                hist.popleft()

    def _stream(self, cmd, handle, timeout=25):
        """Keep one sensor process alive; restart it if it stalls or exits."""
        while self._running:
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                     errors="replace", creationflags=NO_WINDOW)
            except OSError:
                return
            self._procs.append(p)
            if not self._running:
                self._kill(p)
                return
            q = queue.Queue()
            threading.Thread(target=_pump, args=(p, q), daemon=True).start()
            while self._running:
                try:
                    line = q.get(timeout=timeout)
                except queue.Empty:
                    break
                if line is None:
                    break
                try:
                    handle(line)
                except Exception:
                    pass
            self._kill(p)
            if self._running:
                time.sleep(3)

    def _kill(self, proc):
        try:
            proc.kill()
        except Exception:
            pass
        if proc in self._procs:
            self._procs.remove(proc)

    def stop(self):
        self._running = False
        for proc in list(self._procs):
            self._kill(proc)


# ------------------------------------------------------------------ tray ---

ALERT_HIGH = 85.0
ALERT_LOW = 80.0
ALERT_COOLDOWN = 300.0


class AlertLatch:
    """Fires once per over-temperature event, not once per sample."""

    def __init__(self, high=ALERT_HIGH, low=ALERT_LOW, cooldown=ALERT_COOLDOWN):
        self.high = high
        self.low = low
        self.cooldown = cooldown
        self.armed = True
        self.last = -1e9

    def update(self, now, readings):
        if not readings:
            return None
        name, value = max(readings.items(), key=lambda kv: kv[1])
        if value <= self.low:
            self.armed = True
            return None
        if value >= self.high and self.armed and now - self.last >= self.cooldown:
            self.armed = False
            self.last = now
            return name, value
        return None


class Tray:
    """Thin wrapper around pystray; every menu action goes through a queue."""

    def __init__(self, actions, autostart_on, cpu_locked):
        self.actions = actions
        self.autostart_on = autostart_on
        self.cpu_locked = cpu_locked
        self.icon = None
        self.active = False
        self._tip = ""

    def start(self):
        if pystray is None or Image is None:
            return False
        try:
            image = Image.open(BytesIO(base64.b64decode(ICON_PNG))).convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem("Open Tempratur", self._action("open"), default=True),
                pystray.MenuItem("Start with Windows", self._action("autostart"),
                                 checked=lambda item: bool(self.autostart_on())),
                pystray.MenuItem("Enable CPU sensor", self._action("elevate"),
                                 visible=lambda item: bool(self.cpu_locked())),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._action("quit")),
            )
            self.icon = pystray.Icon("Tempratur", image, "Tempratur", menu)
            self.icon.run_detached()
            self.active = True
            return True
        except Exception:
            self.icon = None
            return False

    def _action(self, name):
        def run(icon=None, item=None):
            self.actions.put(name)
        return run

    def notify(self, message, title="Tempratur"):
        if not self.active:
            return
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def tooltip(self, text):
        if not self.active or text == self._tip:
            return
        try:
            self.icon.title = text
            self._tip = text
        except Exception:
            pass

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        self.icon = None
        self.active = False


# ------------------------------------------------------------------ test ---

TEST_SECONDS = 45
TEST_ABORT_AT = 95.0
GPU_TEST_ABORT_AT = 90.0


class CpuStress:
    """Short full-core load. zlib releases the GIL, so the threads really work."""

    def __init__(self, seconds=TEST_SECONDS):
        self.seconds = seconds
        self.started = 0.0
        self._stop = threading.Event()
        self._threads = []

    def start(self):
        if self.active:
            return
        self.started = time.time()
        stop = threading.Event()
        self._stop = stop
        payload = os.urandom(2 * 1024 * 1024)
        for _ in range(min(os.cpu_count() or 4, 16)):
            thread = threading.Thread(target=self._work, args=(payload, stop), daemon=True)
            thread.start()
            self._threads.append(thread)

    def _work(self, payload, stop):
        while not stop.is_set():
            zlib.compress(payload, 6)

    def stop(self):
        self._stop.set()
        self._threads = []

    @property
    def active(self):
        return any(t.is_alive() for t in self._threads)

    @property
    def remaining(self):
        return max(0.0, self.started + self.seconds - time.time())


CUDA_PTX = r"""
.version 6.4
.target sm_50
.address_size 64

.visible .entry burn(
    .param .u64 out,
    .param .u32 iters
)
{
    .reg .f32 %f<19>;
    .reg .u32 %r<8>;
    .reg .u64 %rd<4>;
    .reg .pred %p<2>;

    ld.param.u64 %rd1, [out];
    ld.param.u32 %r1, [iters];
    mov.u32 %r2, %tid.x;
    mov.u32 %r3, %ctaid.x;
    mov.u32 %r4, %ntid.x;
    mad.lo.u32 %r5, %r3, %r4, %r2;

    mov.f32 %f1, 0f3F800000;
    mov.f32 %f2, 0f3F800001;
    mov.f32 %f3, 0f3F800002;
    mov.f32 %f4, 0f3F800003;
    mov.f32 %f5, 0f3F800004;
    mov.f32 %f6, 0f3F800005;
    mov.f32 %f7, 0f3F800006;
    mov.f32 %f8, 0f3F800007;
    mov.f32 %f9, 0f3F800008;
    mov.f32 %f10, 0f3F800009;
    mov.f32 %f11, 0f3F80000A;
    mov.f32 %f12, 0f3F80000B;
    mov.f32 %f13, 0f3F80000C;
    mov.f32 %f14, 0f3F80000D;
    mov.f32 %f15, 0f3F80000E;
    mov.f32 %f16, 0f3F80000F;
    mov.f32 %f17, 0f3F800001;
    mov.f32 %f18, 0f00000001;

    mov.u32 %r6, 0;
LOOP:
    setp.ge.u32 %p1, %r6, %r1;
    @%p1 bra DONE;
    fma.rn.f32 %f1, %f1, %f17, %f18;
    fma.rn.f32 %f2, %f2, %f17, %f18;
    fma.rn.f32 %f3, %f3, %f17, %f18;
    fma.rn.f32 %f4, %f4, %f17, %f18;
    fma.rn.f32 %f5, %f5, %f17, %f18;
    fma.rn.f32 %f6, %f6, %f17, %f18;
    fma.rn.f32 %f7, %f7, %f17, %f18;
    fma.rn.f32 %f8, %f8, %f17, %f18;
    fma.rn.f32 %f9, %f9, %f17, %f18;
    fma.rn.f32 %f10, %f10, %f17, %f18;
    fma.rn.f32 %f11, %f11, %f17, %f18;
    fma.rn.f32 %f12, %f12, %f17, %f18;
    fma.rn.f32 %f13, %f13, %f17, %f18;
    fma.rn.f32 %f14, %f14, %f17, %f18;
    fma.rn.f32 %f15, %f15, %f17, %f18;
    fma.rn.f32 %f16, %f16, %f17, %f18;
    add.u32 %r6, %r6, 1;
    bra LOOP;
DONE:
    add.f32 %f1, %f1, %f2;
    add.f32 %f3, %f3, %f4;
    add.f32 %f5, %f5, %f6;
    add.f32 %f7, %f7, %f8;
    add.f32 %f9, %f9, %f10;
    add.f32 %f11, %f11, %f12;
    add.f32 %f13, %f13, %f14;
    add.f32 %f15, %f15, %f16;
    add.f32 %f1, %f1, %f3;
    add.f32 %f5, %f5, %f7;
    add.f32 %f9, %f9, %f11;
    add.f32 %f13, %f13, %f15;
    add.f32 %f1, %f1, %f5;
    add.f32 %f9, %f9, %f13;
    add.f32 %f1, %f1, %f9;

    mul.wide.u32 %rd2, %r5, 4;
    add.u64 %rd3, %rd1, %rd2;
    st.global.f32 [%rd3], %f1;
    ret;
}
"""


class GpuStress:
    """CUDA load for NVIDIA GPUs, driven through the installed display driver.

    The kernel is hand-written PTX, so the app needs no CUDA toolkit and no
    extra files. Short kernels keep Stop responsive.
    """

    BLOCKS = 128
    THREADS = 256
    ITERS = 300000

    def __init__(self, seconds=TEST_SECONDS):
        self.seconds = seconds
        self.started = 0.0
        self.error = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self.active:
            return
        self.started = time.time()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def failed(self):
        return self.error is not None and not self.active

    @property
    def remaining(self):
        return max(0.0, self.started + self.seconds - time.time())

    @staticmethod
    def _check(cuda, code, what):
        if code:
            name = ctypes.c_char_p()
            try:
                cuda.cuGetErrorName(code, ctypes.byref(name))
                detail = name.value.decode(errors="replace")
            except Exception:
                detail = str(code)
            raise RuntimeError(f"{what}: {detail}")

    def _run(self):
        cuda = None
        ctx = mod = fn = None
        buf = ctypes.c_uint64()
        try:
            cuda = ctypes.WinDLL("nvcuda.dll")
            cuda.cuInit.argtypes = [ctypes.c_uint]
            cuda.cuInit.restype = ctypes.c_int
            cuda.cuDeviceGet.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
            cuda.cuDeviceGet.restype = ctypes.c_int
            cuda.cuCtxCreate_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                            ctypes.c_uint, ctypes.c_int]
            cuda.cuCtxCreate_v2.restype = ctypes.c_int
            cuda.cuCtxDestroy_v2.argtypes = [ctypes.c_void_p]
            cuda.cuCtxDestroy_v2.restype = ctypes.c_int
            cuda.cuModuleLoadDataEx.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                                ctypes.c_void_p, ctypes.c_uint,
                                                ctypes.c_void_p, ctypes.c_void_p]
            cuda.cuModuleLoadDataEx.restype = ctypes.c_int
            cuda.cuModuleGetFunction.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                                 ctypes.c_void_p, ctypes.c_char_p]
            cuda.cuModuleGetFunction.restype = ctypes.c_int
            cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]
            cuda.cuMemAlloc_v2.restype = ctypes.c_int
            cuda.cuMemFree_v2.argtypes = [ctypes.c_uint64]
            cuda.cuMemFree_v2.restype = ctypes.c_int
            cuda.cuLaunchKernel.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                                            ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
            cuda.cuLaunchKernel.restype = ctypes.c_int
            cuda.cuCtxSynchronize.argtypes = []
            cuda.cuCtxSynchronize.restype = ctypes.c_int
            cuda.cuGetErrorName.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
            cuda.cuGetErrorName.restype = ctypes.c_int

            self._check(cuda, cuda.cuInit(0), "cuInit")
            dev = ctypes.c_int()
            self._check(cuda, cuda.cuDeviceGet(ctypes.byref(dev), 0), "cuDeviceGet")
            ctx = ctypes.c_void_p()
            self._check(cuda, cuda.cuCtxCreate_v2(ctypes.byref(ctx), 0, dev), "cuCtxCreate")
            mod = ctypes.c_void_p()
            image = ctypes.cast(ctypes.c_char_p(CUDA_PTX.encode()), ctypes.c_void_p)
            self._check(cuda, cuda.cuModuleLoadDataEx(
                ctypes.byref(mod), image, 0, None, None), "cuModuleLoadDataEx")
            fn = ctypes.c_void_p()
            self._check(cuda, cuda.cuModuleGetFunction(
                ctypes.byref(fn), mod, b"burn"), "cuModuleGetFunction")
            self._check(cuda, cuda.cuMemAlloc_v2(
                ctypes.byref(buf), self.BLOCKS * self.THREADS * 4), "cuMemAlloc")

            iters = ctypes.c_uint32(self.ITERS)
            out = ctypes.c_uint64(buf.value)
            args = (ctypes.c_void_p * 2)(
                ctypes.cast(ctypes.byref(out), ctypes.c_void_p),
                ctypes.cast(ctypes.byref(iters), ctypes.c_void_p),
            )
            end = self.started + self.seconds
            while not self._stop.is_set() and time.time() < end:
                self._check(cuda, cuda.cuLaunchKernel(
                    fn, self.BLOCKS, 1, 1, self.THREADS, 1, 1, 0, None, args, None),
                    "cuLaunchKernel")
                self._check(cuda, cuda.cuCtxSynchronize(), "cuCtxSynchronize")
        except OSError:
            self.error = "CUDA driver not found. Install or update the NVIDIA driver."
        except Exception as exc:
            self.error = str(exc) or "The GPU test could not start."
        finally:
            try:
                if cuda is not None and buf.value:
                    cuda.cuMemFree_v2(buf.value)
                if cuda is not None and ctx is not None and ctx.value:
                    cuda.cuCtxDestroy_v2(ctx)
            except Exception:
                pass


# ------------------------------------------------------------------- ui ----

class Card(tk.Canvas):
    def __init__(self, master, label, unit, fmt, color, scale):
        super().__init__(master, bg=BG, bd=0, highlightthickness=0,
                         width=s(210), height=s(236))
        self.label = label
        self.unit = unit
        self.fmt = fmt
        self.base_color = color
        self.scale = scale
        self.target = None
        self.disp = None
        self.note = ""
        self.tag = ""
        self.tag_color = MUTED
        self.color = color
        self.clickable = False
        self.hover = False
        self._key = None
        self.bind("<Configure>", lambda e: self._rekey())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _rekey(self):
        self._key = None
        self.redraw()

    def _enter(self, _):
        if self.clickable and not self.hover:
            self.hover = True
            self.redraw()

    def _leave(self, _):
        if self.hover:
            self.hover = False
            self.redraw()

    def show(self, value, note="", tag="", tag_color=MUTED, color=None, clickable=False):
        self.target = value
        self.note = note
        self.tag = tag
        self.tag_color = tag_color
        self.color = color or self.base_color
        self.clickable = clickable
        self.configure(cursor="hand2" if clickable else "")
        self._key = None

    def tick(self):
        if self.target is None:
            self.disp = None
        elif self.disp is None:
            self.disp = self.target
        elif self.disp != self.target:
            self.disp += (self.target - self.disp) * 0.2
            if abs(self.target - self.disp) < 0.05:
                self.disp = self.target
        key = (None if self.disp is None else round(self.disp, 2),
               self.note, self.tag, self.color, self.hover)
        if key != self._key:
            self._key = key
            self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40:
            return
        hot = self.color == HOT
        panel = mix(CARD, HOT, 0.05) if hot else CARD
        if self.hover:
            outline = self.color
        elif hot:
            outline = mix(BORDER, HOT, 0.45)
        else:
            outline = BORDER
        rrect(self, 1, 1, w - 1, h - 1, s(16), fill=panel, outline=outline)
        self.create_text(s(20), s(17), text=self.label, anchor="nw", fill=MUTED,
                         font=(SEMI, -s(11)))
        if self.tag:
            self.create_text(w - s(20), s(17), text=self.tag, anchor="ne",
                             fill=self.tag_color, font=(SEMI, -s(10)))

        cx, cy = w / 2, s(111)
        r = min((w - s(64)) / 2, s(71))
        if r < s(24):
            return
        bbox = (cx - r, cy - r, cx + r, cy + r)
        self.create_arc(*bbox, start=135, extent=-270, style="arc",
                        outline=mix(TRACK, HOT, 0.3) if hot else TRACK, width=s(9))
        if self.disp is not None:
            frac = gauge_frac(self.disp, self.scale)
            if frac > 0.004:
                self.create_arc(*bbox, start=135, extent=-270 * frac, style="arc",
                                outline=self.color, width=s(9))
                ex, ey = self._point(135 - 270 * frac, cx, cy, r)
                d = s(5)
                self.create_oval(ex - d, ey - d, ex + d, ey + d,
                                 fill=self.color, outline=panel, width=s(1))

        if self.disp is None:
            self.create_text(cx, cy, text="—", fill=DIM, font=(SEMI, -s(32)))
        else:
            txt = self.fmt(self.disp)
            nw = fnt(38, semi=True).measure(txt)
            uw = fnt(13).measure(self.unit)
            left = cx - (nw + s(4) + uw) / 2
            self.create_text(left, cy, text=txt, anchor="w", fill=TEXT,
                             font=(SEMI, -s(38)))
            self.create_text(left + nw + s(4), cy + s(9), text=self.unit, anchor="w",
                             fill=MUTED, font=(FAM, -s(13)))

        if self.note:
            self.create_text(cx, h - s(24), text=self.note,
                             fill=WARM if self.clickable else DIM,
                             font=(FAM, -s(10)))

    @staticmethod
    def _point(angle, cx, cy, r):
        a = math.radians(angle)
        return cx + r * math.cos(a), cy - r * math.sin(a)


class StatusPill(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg=BG, bd=0, highlightthickness=0,
                         width=s(210), height=s(30))
        self.text = ""
        self.color = DIM
        self.bind("<Configure>", lambda e: self.redraw())

    def show(self, text, color):
        if text == self.text and color == self.color:
            return
        self.text, self.color = text, color
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), s(30)
        if w < s(60):
            return
        pw = fnt(11, semi=True).measure(self.text) + s(40)
        x0 = w - pw
        rrect(self, x0, 1, w - 1, h - 1, s(15), fill=mix(BG, self.color, 0.16),
              outline=mix(BG, self.color, 0.45))
        self.create_oval(x0 + s(12), s(12), x0 + s(18), s(18), fill=self.color, outline="")
        self.create_text(x0 + s(24), s(15), text=self.text, anchor="w", fill=self.color,
                         font=(SEMI, -s(11)))


class Chart(tk.Canvas):
    WINDOW = 120.0
    Y_MIN = 20
    Y_MAX = 100

    def __init__(self, master, sensors):
        super().__init__(master, bg=BG, bd=0, highlightthickness=0,
                         width=s(600), height=s(240))
        self.sensors = sensors
        self.dirty = True
        self.last_draw = 0.0
        self.bind("<Configure>", lambda e: self._force())

    def _force(self):
        self.dirty = True
        self.redraw()

    def maybe_redraw(self, now):
        if self.dirty or now - self.last_draw > 1.0:
            self.dirty = False
            self.last_draw = now
            self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 80 or h < 80:
            return
        rrect(self, 1, 1, w - 1, h - 1, s(16), fill=CARD, outline=BORDER)
        self.create_text(s(20), s(16), text="Temperature history", anchor="nw",
                         fill=TEXT, font=(SEMI, -s(12)))
        self.create_text(s(20), s(34), text="Last two minutes", anchor="nw",
                         fill=DIM, font=(FAM, -s(10)))

        cpu_on = self.sensors.cpu is not None
        gpu_on = self.sensors.gpu is not None
        x = w - s(18)
        for name, color, on in (("GPU", COOL, gpu_on), ("CPU", CPU_BLUE, cpu_on)):
            tw = fnt(10).measure(name)
            self.create_text(x, s(22), text=name, anchor="e",
                             fill=TEXT if on else DIM, font=(FAM, -s(10)))
            self.create_oval(x - tw - s(13), s(19), x - tw - s(5), s(27),
                             fill=color if on else DIM, outline="")
            x -= tw + s(30)

        left, right = s(44), w - s(18)
        top, bottom = s(62), h - s(28)
        if right - left < 40 or bottom - top < 40:
            return

        for v in (20, 40, 60, 80, 100):
            y = bottom - (v - self.Y_MIN) / (self.Y_MAX - self.Y_MIN) * (bottom - top)
            hot = v == 80
            self.create_line(left, y, right, y,
                             fill=mix(HOT, BORDER, 0.62) if hot else BORDER,
                             dash=(2, 4))
            self.create_text(left - s(8), y, text=str(v), anchor="e",
                             fill=mix(HOT, MUTED, 0.4) if hot else DIM,
                             font=(FAM, -s(9)))

        now = time.time()
        t0 = now - self.WINDOW

        def px(t):
            return left + (t - t0) / self.WINDOW * (right - left)

        def py(v):
            return bottom - (v - self.Y_MIN) / (self.Y_MAX - self.Y_MIN) * (bottom - top)

        self.create_text(left, bottom + s(12), text="2 min ago", anchor="w",
                         fill=DIM, font=(FAM, -s(9)))
        self.create_text((left + right) / 2, bottom + s(12), text="1 min", anchor="center",
                         fill=DIM, font=(FAM, -s(9)))
        self.create_text(right, bottom + s(12), text="now", anchor="e",
                         fill=DIM, font=(FAM, -s(9)))

        series = ((self.sensors.cpu_hist, CPU_BLUE, "#0C1622"),
                  (self.sensors.gpu_hist, COOL, "#0B1B15"))
        drawn = 0
        for hist, color, fill in series:
            pts = [(px(t), py(v)) for t, v in hist if t >= t0]
            if len(pts) < 2:
                continue
            drawn += 1
            flat = [c for p in pts for c in p]
            self.create_polygon([pts[0][0], bottom] + flat + [pts[-1][0], bottom],
                                fill=fill, outline="")
            self.create_line(flat, fill=color, width=s(2))
            ex, ey = pts[-1]
            d = s(3)
            self.create_oval(ex - d, ey - d, ex + d, ey + d, fill=color, outline=CARD)

        if not drawn:
            self.create_text((left + right) / 2, (top + bottom) / 2,
                             text="Waiting for the first readings", fill=DIM,
                             font=(FAM, -s(11)))


class App:
    TEMP_SCALE = (20, 100)
    SUBTITLE = "Internal sensors, read every two seconds."

    def __init__(self, root, start_hidden=False):
        self.root = root
        self.sensors = Sensors()
        self.actions = queue.Queue()
        self.tray = Tray(self.actions, autostart_enabled, self.cpu_locked)
        self.alerts = AlertLatch()
        self.test = None
        self.test_kind = None
        self.test_peak = None
        self.test_note = ""
        self.test_note_until = 0.0
        self.last_pull = 0.0
        self.last_cpu_t = 0.0
        self.last_gpu_t = 0.0
        self.cards = []
        self.hint_shown = False
        self.closed = False
        self.build()
        self.tray.start()
        self.sensors.start()
        if start_hidden and self.tray.active:
            root.withdraw()
        root.after(60, self.tick)

    # -- layout ------------------------------------------------------------

    def build(self):
        root = self.root
        root.title("Tempratur")
        try:
            self._icon = tk.PhotoImage(data=ICON_PNG)
            root.iconphoto(True, self._icon)
        except Exception:
            pass
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<Escape>", lambda e: self.on_close())
        root.bind("<Control-q>", lambda e: self.quit())
        root.bind("<Control-t>", lambda e: self.toggle_test("CPU"))
        root.bind("<Control-g>", lambda e: self.toggle_test("GPU"))

        w = min(s(1060), int(root.winfo_screenwidth() * 0.94))
        h = min(s(700), int(root.winfo_screenheight() * 0.90))
        x = (root.winfo_screenwidth() - w) // 2
        y = max(0, (root.winfo_screenheight() - h) // 2 - s(18))
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(s(900), s(600))
        root.columnconfigure(0, weight=1)

        header = tk.Frame(root, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=s(22), pady=(s(18), 0))
        header.columnconfigure(0, weight=1)
        titles = tk.Frame(header, bg=BG)
        titles.grid(row=0, column=0, sticky="w")
        tk.Label(titles, text="Tempratur", bg=BG, fg=TEXT,
                 font=(SEMI, -s(24))).pack(anchor="w")
        self.subtitle = tk.Label(titles, text=self.SUBTITLE, bg=BG,
                                 fg=MUTED, font=(FAM, -s(11)))
        self.subtitle.pack(anchor="w", pady=(s(1), 0))
        self.pill = StatusPill(header)
        self.pill.grid(row=0, column=1, sticky="e")

        row = tk.Frame(root, bg=BG)
        row.grid(row=1, column=0, sticky="ew", padx=s(22), pady=(s(16), 0))
        self.cpu_card = Card(row, "CPU", "°C", lambda v: f"{v:.0f}", CPU_BLUE, self.TEMP_SCALE)
        self.gpu_card = Card(row, "GPU", "°C", lambda v: f"{v:.0f}", COOL, self.TEMP_SCALE)
        self.load_card = Card(row, "CPU LOAD", "%", lambda v: f"{v:.0f}", CPU_BLUE, (0, 100))
        self.mem_card = Card(row, "MEMORY", "%", lambda v: f"{v:.0f}", MEM_PURPLE, (0, 100))
        self.cards = [self.cpu_card, self.gpu_card, self.load_card, self.mem_card]
        for i, card in enumerate(self.cards):
            row.columnconfigure(i, weight=1, uniform="card")
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else s(12), 0))
        self.cpu_card.bind("<Button-1>", lambda e: self.enable_cpu())

        self.chart = Chart(root, self.sensors)
        self.chart.grid(row=2, column=0, sticky="nsew", padx=s(22), pady=(s(16), 0))
        root.rowconfigure(2, weight=1)

        footer = tk.Frame(root, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", padx=s(22), pady=(s(10), s(14)))
        footer.columnconfigure(0, weight=1)
        self.source_label = tk.Label(footer, text="Starting sensor readers.", bg=BG,
                                     fg=DIM, font=(FAM, -s(10)))
        self.source_label.grid(row=0, column=0, sticky="w")
        actions = tk.Frame(footer, bg=BG)
        actions.grid(row=0, column=1, padx=(s(10), 0))
        self.cpu_btn = tk.Button(actions, text="Test CPU",
                                 command=lambda: self.toggle_test("CPU"),
                                 bg=CARD, fg=TEXT, activebackground=CARD_HOVER,
                                 activeforeground=TEXT, relief="flat", bd=0,
                                 font=(SEMI, -s(10)), cursor="hand2",
                                 padx=s(14), pady=s(6), highlightthickness=0)
        self.cpu_btn.pack(side="left")
        self.gpu_btn = tk.Button(actions, text="Test GPU",
                                 command=lambda: self.toggle_test("GPU"),
                                 bg=CARD, fg=TEXT, activebackground=CARD_HOVER,
                                 activeforeground=TEXT, relief="flat", bd=0,
                                 font=(SEMI, -s(10)), cursor="hand2",
                                 padx=s(14), pady=s(6), highlightthickness=0,
                                 state="disabled", disabledforeground=DIM)
        self.gpu_btn.pack(side="left", padx=(s(8), 0))
        self.enable_btn = tk.Button(footer, text="Enable CPU sensor", command=self.enable_cpu,
                                    bg=CARD, fg=WARM, activebackground=CARD_HOVER,
                                    activeforeground=WARM, relief="flat", bd=0,
                                    font=(SEMI, -s(10)), cursor="hand2",
                                    padx=s(14), pady=s(6), highlightthickness=0)
        self.updated_label = tk.Label(footer, text="", bg=BG, fg=DIM, font=(FAM, -s(10)))
        self.updated_label.grid(row=0, column=3, sticky="e")

        root.update_idletasks()
        self.dark_titlebar()

    def dark_titlebar(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            on = ctypes.c_int(1)
            for attr in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                    break
            r, g, b = (int(BG[i:i + 2], 16) for i in (1, 3, 5))
            color = ctypes.c_uint(r | (g << 8) | (b << 16))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
        except Exception:
            pass

    # -- behaviour ---------------------------------------------------------

    def cpu_locked(self):
        return self.sensors.cpu is None and self.sensors.cpu_lock == "denied"

    def enable_cpu(self):
        if self.sensors.cpu is not None:
            return
        args = None
        if not getattr(sys, "frozen", False):
            args = f'"{os.path.abspath(__file__)}"'
        try:
            code = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, args, None, 1)
        except Exception:
            return
        if code > 32:
            self.quit()

    def on_close(self):
        if not self.tray.active:
            self.quit()
            return
        self.root.withdraw()
        if not self.hint_shown:
            self.hint_shown = True
            self.tray.notify(
                "Tempratur keeps running here. Right-click the icon to quit.",
                "Still monitoring")

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_autostart(self):
        on = not autostart_enabled()
        if set_autostart(on):
            self.tray.notify("Tempratur will start with Windows." if on
                             else "Tempratur will no longer start with Windows.")

    def toggle_test(self, kind="CPU"):
        if self.test_kind is not None:
            if self.test_kind == kind:
                self._finish_test("stopped")
            return
        if kind == "GPU" and not self.sensors.gpu_seen:
            return
        self.test = CpuStress() if kind == "CPU" else GpuStress()
        self.test_kind = kind
        self.test_peak = None
        self.test_note_until = 0.0
        self.test.start()
        self.cpu_btn.config(text="Stop test" if kind == "CPU" else "Test CPU",
                            fg=HOT if kind == "CPU" else TEXT,
                            state="normal" if kind == "CPU" else "disabled")
        self.gpu_btn.config(text="Stop test" if kind == "GPU" else "Test GPU",
                            fg=HOT if kind == "GPU" else TEXT,
                            state="normal" if kind == "GPU" else "disabled")
        self.subtitle.config(text=f"{kind} stress test · {self.test.seconds}s left", fg=WARM)

    def _finish_test(self, reason="done"):
        if self.test_kind is None:
            return
        kind = self.test_kind
        peak = self.test_peak
        seconds = self.test.seconds
        error = getattr(self.test, "error", None)
        self.test.stop()
        self.test_kind = None
        self.test_note_until = time.time() + 12
        if reason == "hot":
            self.test_note = f"Stopped early · {kind} hit {peak:.0f}°C"
            self.tray.notify(f"The {kind} hit {peak:.0f}°C, so the test stopped early.",
                             "Test stopped")
        elif reason == "error":
            self.test_note = f"GPU test failed · {error or 'CUDA is not available'}"
            self.tray.notify(error or "CUDA is not available.", "GPU test failed")
        elif reason == "stopped":
            self.test_note = (f"Test stopped · {kind} peaked at {peak:.0f}°C"
                              if peak is not None else "Test stopped")
        elif peak is not None:
            self.test_note = f"Test finished · {kind} peaked at {peak:.0f}°C"
            self.tray.notify(f"{kind} peaked at {peak:.0f}°C during the {seconds}s test.",
                             "Test finished")
        else:
            self.test_note = f"Test finished · {kind} sensor unavailable"
        self.cpu_btn.config(text="Test CPU", fg=TEXT, state="normal")
        self.gpu_btn.config(text="Test GPU", fg=TEXT,
                            state="normal" if self.sensors.gpu_seen else "disabled")
        self.subtitle.config(text=self.test_note, fg=MUTED)

    def quit(self):
        if self.closed:
            return
        self.closed = True
        if self.test is not None:
            self.test.stop()
        self.sensors.stop()
        self.tray.stop()
        self.root.destroy()

    def tick(self):
        while True:
            try:
                action = self.actions.get_nowait()
            except queue.Empty:
                break
            if action == "open":
                self.show_window()
            elif action == "autostart":
                self.toggle_autostart()
            elif action == "elevate":
                self.enable_cpu()
            elif action == "quit":
                self.quit()
        if self.closed:
            return
        now = time.time()
        if now - self.last_pull >= 1.0:
            self.last_pull = now
            self.pull(now)
        for card in self.cards:
            card.tick()
        self.chart.maybe_redraw(now)
        try:
            self.root.after(60, self.tick)
        except tk.TclError:
            pass

    def pull(self, now):
        sen = self.sensors
        testing = self.test_kind is not None
        if sen.cpu is not None and sen.cpu_t > self.last_cpu_t:
            self.last_cpu_t = sen.cpu_t
            sen.cpu_hist.append((sen.cpu_t, sen.cpu))
            self.chart.dirty = True
        if sen.gpu is not None and sen.gpu_t > self.last_gpu_t:
            self.last_gpu_t = sen.gpu_t
            sen.gpu_hist.append((sen.gpu_t, sen.gpu))
            self.chart.dirty = True
        sen.prune(now)

        if sen.cpu is not None:
            self.cpu_card.show(sen.cpu, color=temp_color(sen.cpu), tag=state_word(sen.cpu).upper(),
                               tag_color=temp_color(sen.cpu),
                               note=f"low {sen.lo['cpu']:.0f}°   high {sen.hi['cpu']:.0f}°")
        elif sen.cpu_lock == "denied":
            self.cpu_card.show(None, tag="LOCKED", tag_color=WARM,
                               note="Click to grant access", clickable=True)
        elif sen.cpu_lock == "none":
            self.cpu_card.show(None, tag="NO SENSOR", note="No readable CPU sensor")
        else:
            self.cpu_card.show(None, note="Reading the sensor...")

        if sen.gpu is not None:
            self.gpu_card.show(sen.gpu, color=temp_color(sen.gpu), tag=state_word(sen.gpu).upper(),
                               tag_color=temp_color(sen.gpu),
                               note=f"low {sen.lo['gpu']:.0f}°   high {sen.hi['gpu']:.0f}°")
        elif sen.gpu_seen:
            self.gpu_card.show(None, tag="NO DATA", note="Waiting for the driver")
        else:
            self.gpu_card.show(None, note="No NVIDIA GPU found")

        if psutil:
            load = psutil.cpu_percent(None)
            try:
                freq = f"{psutil.cpu_freq().current / 1000:.2f} GHz"
            except Exception:
                freq = ""
            threads = psutil.cpu_count(logical=True) or 0
            self.load_card.show(load, note=" · ".join(x for x in (freq, f"{threads} threads") if x))
            mem = psutil.virtual_memory()
            self.mem_card.show(mem.percent,
                               note=f"{mem.used / 2**30:.1f} of {mem.total / 2**30:.1f} GB")
        else:
            self.load_card.show(None, note="psutil not installed")
            self.mem_card.show(None, note="psutil not installed")

        temps = [v for v in (sen.cpu, sen.gpu) if v is not None]
        if not temps:
            self.pill.show("Waiting for sensors", DIM)
        else:
            both = sen.cpu is not None and sen.gpu is not None
            prefix = "Everything" if both else ("CPU" if sen.cpu is not None else "GPU")
            peak = max(temps)
            self.pill.show(f"{prefix} {state_word(peak)}", temp_color(peak))

        if testing:
            value = sen.cpu if self.test_kind == "CPU" else sen.gpu
            limit = TEST_ABORT_AT if self.test_kind == "CPU" else GPU_TEST_ABORT_AT
            if value is not None:
                self.test_peak = (value if self.test_peak is None
                                  else max(self.test_peak, value))
                if value >= limit:
                    self._finish_test("hot")
            if self.test_kind == "GPU" and self.test.failed:
                self._finish_test("error")
            if self.test_kind is not None and self.test.remaining <= 0:
                self._finish_test("done")

        readings = {}
        if sen.cpu is not None:
            readings["CPU"] = sen.cpu
        if sen.gpu is not None:
            readings["GPU"] = sen.gpu
        hit = self.alerts.update(now, readings)
        if hit and not testing:
            name, value = hit
            self.tray.notify(f"{name} reached {value:.0f}°C. Let the machine cool down.",
                             "High temperature")
        self.tray.tooltip(" · ".join(f"{k} {v:.0f}°" for k, v in readings.items())
                          or "Tempratur")

        src = []
        if sen.cpu is not None:
            src.append("ACPI thermal zone")
        if sen.gpu_seen:
            src.append(sen.gpu_name)
        line = "Sensors: " + (" + ".join(src) if src else "starting up")
        if sen.cpu_lock == "denied":
            line += "   ·   CPU sensor needs admin"
        self.source_label.config(text=line)

        stamps = [t for t in (sen.cpu_t, sen.gpu_t) if t]
        if stamps:
            age = max(0.0, now - max(stamps))
            if age < 1.5:
                self.updated_label.config(text="Updated just now", fg=DIM)
            elif age < 10:
                self.updated_label.config(text=f"Updated {age:.0f}s ago", fg=DIM)
            else:
                self.updated_label.config(text="No fresh readings", fg=WARM)
        else:
            self.updated_label.config(text="No readings yet", fg=DIM)

        if self.test_kind is not None:
            left = math.ceil(self.test.remaining)
            self.subtitle.config(text=f"{self.test_kind} stress test · {left}s left", fg=WARM)
            if self.test_kind == "CPU":
                self.cpu_btn.config(text="Stop test", fg=HOT)
            else:
                self.gpu_btn.config(text="Stop test", fg=HOT)
        else:
            if sen.gpu_seen:
                self.gpu_btn.config(state="normal")
            if now < self.test_note_until:
                self.subtitle.config(text=self.test_note, fg=MUTED)
            else:
                self.subtitle.config(text=self.SUBTITLE, fg=MUTED)

        if sen.cpu_lock == "denied":
            self.enable_btn.grid(row=0, column=2, padx=(s(10), s(14)))
        else:
            self.enable_btn.grid_remove()


# ------------------------------------------------------------------ main ---

def main():
    enable_dpi()
    if not first_instance():
        return
    root = tk.Tk()
    App(root, start_hidden="--tray" in sys.argv)
    root.mainloop()


def selftest():
    assert num("58.2") == 58.2
    assert num("45, 12") == 45.0
    assert num("[N/A]") is None
    assert num("denied") is None
    assert parse_temp("58.2") == 58.2
    assert parse_temp("2.0") is None
    assert parse_temp("0") is None
    assert temp_color(59.9) == COOL and temp_color(60) == WARM and temp_color(80) == HOT
    assert gauge_frac(20, (20, 100)) == 0 and gauge_frac(110, (20, 100)) == 1
    assert abs(gauge_frac(60, (20, 100)) - 0.5) < 1e-9
    assert mix("#000000", "#ffffff", 0.5) == "#7f7f7f"

    latch = AlertLatch(85, 80, 300)
    assert latch.update(0, {"CPU": 84}) is None
    assert latch.update(1, {"CPU": 86}) == ("CPU", 86)
    assert latch.update(2, {"CPU": 97}) is None
    assert latch.update(3, {"CPU": 79}) is None
    assert latch.update(4, {"CPU": 95}) is None
    assert latch.update(301, {"CPU": 95}) == ("CPU", 95)
    assert AlertLatch(85, 80, 0).update(0, {"CPU": 81, "GPU": 90}) == ("GPU", 90)
    assert "--tray" in launch_command()
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    try:
        main()
    except Exception:
        try:
            with open(os.path.join(app_dir(), "tempratur-error.log"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise
