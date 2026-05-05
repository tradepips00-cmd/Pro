
import os
import sys
import json
import time
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import psutil
except Exception:
    psutil = None

APP_NAME = "GameLoop Magic Booster Pro"
APP_VERSION = "2.0 PRO"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

BG = "#050805"
PANEL = "#0a120c"
PANEL2 = "#101c12"
GREEN = "#00ff3c"
GREEN2 = "#7dff00"
CYAN = "#00eaff"
RED = "#ff2d2d"
YELLOW = "#ffe14d"
WHITE = "#f5fff5"
MUTED = "#9be7a8"

GAMELOOP_EXE_NAMES = [
    "AndroidEmulatorEx.exe", "AndroidEmulator.exe", "aow_exe.exe",
    "AppMarket.exe", "GameLoop.exe", "TGB.exe",
]

COMMON_GAMELOOP_PATHS = [
    r"C:\Program Files\TxGameAssistant\AppMarket\AppMarket.exe",
    r"C:\Program Files (x86)\Tencent\TxGameAssistant\AppMarket\AppMarket.exe",
    r"C:\Program Files\Tencent\TxGameAssistant\AppMarket\AppMarket.exe",
    r"C:\Program Files (x86)\TxGameAssistant\AppMarket\AppMarket.exe",
    r"D:\Program Files\TxGameAssistant\AppMarket\AppMarket.exe",
    r"D:\Program Files (x86)\Tencent\TxGameAssistant\AppMarket\AppMarket.exe",
]

OVERLAY_PROCESS_HINTS = [
    "GameBar.exe", "GameBarFTServer.exe", "XboxPcApp.exe",
    "Discord.exe", "NVIDIA Share.exe", "RadeonSoftware.exe",
]

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_cmd(cmd, timeout=10):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)

def load_config():
    cfg = {
        "gameloop_path": "",
        "cores": "all",
        "profile": "Ultra Stability",
        "lock_interval": 1.0,
        "silent_mode": True,
        "fps_guard": True,
        "network_guard": True,
        "overlay_quiet": True,
        "gpu_preference": True,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            cfg.update(json.loads(open(CONFIG_FILE, "r", encoding="utf-8").read()))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    open(CONFIG_FILE, "w", encoding="utf-8").write(json.dumps(cfg, indent=2))

def get_cpu_info():
    cpu_name = os.environ.get("PROCESSOR_IDENTIFIER", "Onbekende CPU")
    logical = os.cpu_count() or 1
    physical = 0
    freq = "Onbekend"
    usage = 0
    ram = 0
    if psutil:
        logical = psutil.cpu_count(True) or logical
        physical = psutil.cpu_count(False) or 0
        f = psutil.cpu_freq()
        freq = f"{f.current:.0f} MHz" if f else "Onbekend"
        usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
    return cpu_name, physical, logical, freq, usage, ram

def get_gpu_info():
    if sys.platform != "win32":
        return "Windows GPU detectie vereist"
    code, out = run_cmd("wmic path win32_VideoController get name", 5)
    lines = [x.strip() for x in out.splitlines() if x.strip() and x.strip().lower() != "name"]
    return " | ".join(lines) if lines else "Onbekend"

def find_gameloop():
    for p in COMMON_GAMELOOP_PATHS:
        if os.path.exists(p):
            return p
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), "C:\\", "D:\\", "E:\\"]
    for root in [r for r in roots if r and os.path.exists(r)]:
        try:
            for dirpath, _, filenames in os.walk(root):
                if len(dirpath.split(os.sep)) > 8:
                    continue
                for fn in filenames:
                    if fn in GAMELOOP_EXE_NAMES:
                        full = os.path.join(dirpath, fn)
                        if any(x.lower() in full.lower() for x in ["gameloop", "tencent", "txgameassistant"]):
                            return full
        except Exception:
            pass
    return ""

def trim_ram():
    if not psutil:
        return "psutil ontbreekt."
    if sys.platform != "win32":
        return "RAM Cleaner is voor Windows."
    count = 0
    psapi = ctypes.WinDLL("psapi.dll")
    kernel32 = ctypes.WinDLL("kernel32.dll")
    empty_ws = psapi.EmptyWorkingSet
    OpenProcess = kernel32.OpenProcess
    CloseHandle = kernel32.CloseHandle
    OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    OpenProcess.restype = ctypes.wintypes.HANDLE
    flags = 0x0400 | 0x0100 | 0x0010
    for proc in psutil.process_iter(["pid"]):
        try:
            pid = proc.info["pid"]
            if pid in (0, 4):
                continue
            h = OpenProcess(flags, False, pid)
            if h:
                if empty_ws(h):
                    count += 1
                CloseHandle(h)
        except Exception:
            pass
    return f"Spike Clean klaar: {count} processen getrimd."

def set_power_mode():
    run_cmd("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", 5)
    code, _ = run_cmd("powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61", 5)
    if code != 0:
        run_cmd("powercfg /setactive SCHEME_MIN", 5)
    return "Power Mode: Ultimate/High Performance actief."

def network_fix():
    cmds = [
        "ipconfig /flushdns",
        "netsh int tcp set global autotuninglevel=normal",
        "netsh int tcp set global rss=enabled",
        "netsh int tcp set global timestamps=disabled",
    ]
    ok = 0
    for cmd in cmds:
        code, _ = run_cmd(cmd, 8)
        ok += code == 0
    return f"Connectivity Fix klaar: {ok}/{len(cmds)} netwerk-tweaks toegepast."

def gpu_preference(exe_path):
    if not exe_path or not os.path.exists(exe_path):
        return "GPU voorkeur: GameLoop EXE niet gevonden."
    if sys.platform != "win32":
        return "GPU voorkeur: alleen Windows."
    try:
        import winreg
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\DirectX\UserGpuPreferences")
        winreg.SetValueEx(key, exe_path, 0, winreg.REG_SZ, "GpuPreference=2;")
        winreg.CloseKey(key)
        return "GPU Preference: High Performance gezet."
    except Exception as e:
        return f"GPU Preference mislukt: {e}"

def input_boost():
    if sys.platform != "win32":
        return "Input Boost is alleen Windows."
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", 0, winreg.KEY_SET_VALUE)
        for name in ["MouseSpeed", "MouseThreshold1", "MouseThreshold2"]:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, "0")
        winreg.CloseKey(key)
        return "Mouse & Keyboard Boost actief: mouse acceleration uit."
    except Exception as e:
        return f"Input Boost mislukt: {e}"

def quiet_overlays():
    if not psutil:
        return "psutil ontbreekt."
    changed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"] or ""
            if name in OVERLAY_PROCESS_HINTS:
                psutil.Process(proc.info["pid"]).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                changed.append(name)
        except Exception:
            pass
    return "Overlays/Junk stilgezet: " + (", ".join(sorted(set(changed))) if changed else "geen overlay gevonden")

def gameloop_procs():
    if not psutil:
        return []
    result = []
    targets = [x.lower() for x in GAMELOOP_EXE_NAMES]
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name in targets or "aow" in name or "gameloop" in name:
                result.append(psutil.Process(proc.info["pid"]))
        except Exception:
            pass
    return result

def apply_engine(core_list=None, priority="high"):
    if not psutil:
        return "psutil ontbreekt."
    touched = []
    for p in gameloop_procs():
        try:
            if core_list is not None:
                p.cpu_affinity(core_list)
            if sys.platform == "win32":
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            touched.append(f"{p.name()}({p.pid})")
        except Exception:
            pass
    return "Engine lock: " + (", ".join(touched) if touched else "geen GameLoop/AOW proces actief")

class GlowButton(tk.Button):
    def __init__(self, master, **kw):
        super().__init__(
            master,
            bg=kw.pop("bg", "#09a51c"),
            fg=kw.pop("fg", "white"),
            activebackground=kw.pop("activebackground", "#29ff42"),
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=kw.pop("font", ("Segoe UI", 11, "bold")),
            padx=kw.pop("padx", 14),
            pady=kw.pop("pady", 10),
            **kw
        )

class ProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1050, 650)
        self.configure(bg=BG)
        self.lock_running = False
        self.monitor_running = True
        self.cpu_name, self.physical, self.logical, self.freq, _, _ = get_cpu_info()
        self.gpu_name = get_gpu_info()

        self.path_var = tk.StringVar(value=self.cfg.get("gameloop_path") or find_gameloop())
        self.core_var = tk.StringVar(value=str(self.cfg.get("cores", "all")))
        self.profile_var = tk.StringVar(value=self.cfg.get("profile", "Ultra Stability"))
        self.silent_var = tk.BooleanVar(value=self.cfg.get("silent_mode", True))
        self.guard_var = tk.BooleanVar(value=self.cfg.get("fps_guard", True))
        self.network_var = tk.BooleanVar(value=self.cfg.get("network_guard", True))
        self.overlay_var = tk.BooleanVar(value=self.cfg.get("overlay_quiet", True))
        self.gpu_var = tk.BooleanVar(value=self.cfg.get("gpu_preference", True))

        self.build_style()
        self.build_layout()
        self.show_home()
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def build_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TCombobox", fieldbackground="#102015", background="#102015", foreground=WHITE, arrowcolor=GREEN)
        self.style.configure("Horizontal.TProgressbar", troughcolor="#142117", background=GREEN, bordercolor=PANEL, lightcolor=GREEN, darkcolor=GREEN)

    def build_layout(self):
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.main, bg="#030603", width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="⚡", bg="#030603", fg=GREEN, font=("Segoe UI", 36, "bold")).pack(pady=(22, 0))
        tk.Label(self.sidebar, text="MAGIC BOOSTER", bg="#030603", fg=WHITE, font=("Segoe UI", 17, "bold")).pack()
        tk.Label(self.sidebar, text="PRO GAMING ENGINE", bg="#030603", fg=GREEN, font=("Segoe UI", 9, "bold")).pack(pady=(0, 22))

        self.menu = [
            ("🏠 HOME DASHBOARD", self.show_home),
            ("🧹 RAM CLEANER", self.show_ram),
            ("🌐 CONNECTIVITY FIX", self.show_net),
            ("🖥 PC OPTIMIZE", self.show_pc),
            ("🎮 FPS BOOST", self.show_fps),
            ("🖱 INPUT BOOST", self.show_input),
            ("🚀 GAMELOOP ENGINE", self.show_engine),
        ]
        for text, cmd in self.menu:
            GlowButton(self.sidebar, text=text, command=cmd, anchor="w").pack(fill="x", padx=18, pady=6)

        tk.Label(self.sidebar, text="STATUS", bg="#030603", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=24, pady=(22, 2))
        self.status_pill = tk.Label(self.sidebar, text="READY", bg=GREEN, fg="#001800", font=("Segoe UI", 11, "bold"), padx=10, pady=8)
        self.status_pill.pack(fill="x", padx=22, pady=4)

        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(side="right", fill="both", expand=True)

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def title(self, text, sub=""):
        tk.Label(self.content, text=text, bg=BG, fg=GREEN, font=("Segoe UI", 27, "bold")).pack(anchor="w", padx=30, pady=(22, 0))
        if sub:
            tk.Label(self.content, text=sub, bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w", padx=32, pady=(2, 8))

    def card(self, parent, title):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground="#183a20", highlightthickness=1)
        tk.Label(frame, text=title, bg=PANEL, fg=GREEN, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        return frame

    def log(self, text):
        self.status_pill.config(text="ACTIVE", bg=GREEN)
        try:
            self.logbox.insert("end", f"{time.strftime('%H:%M:%S')}  {text}\n")
            self.logbox.see("end")
        except Exception:
            pass

    def save(self):
        self.cfg.update({
            "gameloop_path": self.path_var.get(),
            "cores": self.core_var.get(),
            "profile": self.profile_var.get(),
            "silent_mode": self.silent_var.get(),
            "fps_guard": self.guard_var.get(),
            "network_guard": self.network_var.get(),
            "overlay_quiet": self.overlay_var.get(),
            "gpu_preference": self.gpu_var.get(),
        })
        save_config(self.cfg)

    def core_list(self):
        val = self.core_var.get()
        if val == "all":
            return None
        n = max(1, min(int(val), self.logical))
        return list(range(n))

    def stat_box(self, parent, label, value):
        f = tk.Frame(parent, bg=PANEL2, highlightbackground="#1d3d21", highlightthickness=1)
        tk.Label(f, text=label, bg=PANEL2, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(f, text=value, bg=PANEL2, fg=WHITE, font=("Segoe UI", 13, "bold"), wraplength=250, justify="left").pack(anchor="w", padx=12, pady=(2, 12))
        return f

    def show_home(self):
        self.clear()
        self.title("HOME DASHBOARD", "Professionele GameLoop/TGB optimizer met Magic Start hoofdknop.")

        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", padx=30, pady=12)

        self.stat_box(top, "CPU", self.cpu_name[:55]).grid(row=0, column=0, sticky="nsew", padx=6)
        self.stat_box(top, "CORES", f"{self.physical} physical / {self.logical} logical").grid(row=0, column=1, sticky="nsew", padx=6)
        self.stat_box(top, "GPU", self.gpu_name[:55]).grid(row=0, column=2, sticky="nsew", padx=6)
        self.stat_box(top, "ADMIN", "YES" if is_admin() else "NO - run as Administrator").grid(row=0, column=3, sticky="nsew", padx=6)
        for i in range(4): top.columnconfigure(i, weight=1)

        mid = tk.Frame(self.content, bg=BG)
        mid.pack(fill="both", expand=True, padx=30, pady=8)

        left = self.card(mid, "Live Performance Monitor")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.cpu_label = tk.Label(left, text="CPU: --%", bg=PANEL, fg=WHITE, font=("Segoe UI", 12, "bold"))
        self.cpu_label.pack(anchor="w", padx=16, pady=4)
        self.cpu_bar = ttk.Progressbar(left, orient="horizontal", mode="determinate", maximum=100)
        self.cpu_bar.pack(fill="x", padx=16, pady=4)
        self.ram_label = tk.Label(left, text="RAM: --%", bg=PANEL, fg=WHITE, font=("Segoe UI", 12, "bold"))
        self.ram_label.pack(anchor="w", padx=16, pady=(12, 4))
        self.ram_bar = ttk.Progressbar(left, orient="horizontal", mode="determinate", maximum=100)
        self.ram_bar.pack(fill="x", padx=16, pady=4)

        self.logbox = tk.Text(left, height=14, bg="#030603", fg=MUTED, insertbackground=WHITE, relief="flat", font=("Consolas", 10))
        self.logbox.pack(fill="both", expand=True, padx=16, pady=16)

        right = self.card(mid, "GameLoop Engine Control")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(right, text="GameLoop/TGB EXE", bg=PANEL, fg=WHITE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill="x", padx=16, pady=6)
        tk.Entry(row, textvariable=self.path_var, bg="#102015", fg=WHITE, insertbackground=WHITE, relief="flat").pack(side="left", fill="x", expand=True, ipady=8)
        GlowButton(row, text="Auto Find", command=self.auto_find, padx=10, pady=7).pack(side="left", padx=8)
        GlowButton(row, text="Browse", command=self.browse, padx=10, pady=7).pack(side="left")

        tk.Label(right, text="All Cores / CPU Affinity", bg=PANEL, fg=WHITE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(10, 0))
        ttk.Combobox(right, textvariable=self.core_var, state="readonly", values=["all"] + [str(i) for i in range(1, self.logical + 1)]).pack(fill="x", padx=16, pady=6)

        tk.Label(right, text="Performance Profile", bg=PANEL, fg=WHITE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(8, 0))
        ttk.Combobox(right, textvariable=self.profile_var, state="readonly", values=["Balanced Boost", "Ultra Stability", "Max Performance"]).pack(fill="x", padx=16, pady=6)

        for label, var in [
            ("FPS Drop Guard: lock elke 1 sec AOW/GameLoop", self.guard_var),
            ("Connectivity Guard / netwerk stabiel", self.network_var),
            ("Overlays/Junk stilzetten", self.overlay_var),
            ("GPU High-Performance preference", self.gpu_var),
            ("Silent Mode: tool maakt zelf geen lag", self.silent_var),
        ]:
            tk.Checkbutton(right, text=label, variable=var, bg=PANEL, fg=WHITE, selectcolor="#102015",
                           activebackground=PANEL, activeforeground=WHITE, font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=3)

        GlowButton(right, text="✨ MAGIC START", command=self.magic_start, font=("Segoe UI", 22, "bold"), pady=18).pack(fill="x", padx=16, pady=18)
        GlowButton(right, text="STOP GUARD", command=self.stop_guard, bg="#9b0000", activebackground=RED, font=("Segoe UI", 13, "bold")).pack(fill="x", padx=16, pady=(0, 18))

        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

    def auto_find(self):
        path = find_gameloop()
        if path:
            self.path_var.set(path)
            self.save()
            self.log(f"GameLoop gevonden: {path}")
        else:
            self.log("GameLoop niet gevonden. Gebruik Browse.")

    def browse(self):
        path = filedialog.askopenfilename(title="Kies GameLoop/TGB exe", filetypes=[("EXE", "*.exe")])
        if path:
            self.path_var.set(path)
            self.save()
            self.log(f"EXE gekozen: {path}")

    def launch_gameloop(self):
        path = self.path_var.get().strip('"')
        if not path or not os.path.exists(path):
            path = find_gameloop()
            self.path_var.set(path)
        if path and os.path.exists(path):
            subprocess.Popen([path], cwd=os.path.dirname(path))
            return "GameLoop/TGB gestart."
        return "GameLoop/TGB niet gevonden."

    def start_guard(self):
        self.save()
        if self.lock_running:
            self.log("FPS Drop Guard draait al.")
            return
        self.lock_running = True
        threading.Thread(target=self.guard_loop, daemon=True).start()
        self.log("FPS Drop Guard actief: lock elke 1 sec.")

    def stop_guard(self):
        self.lock_running = False
        self.status_pill.config(text="READY", bg=GREEN2)
        self.log("Guard gestopt.")

    def guard_loop(self):
        while self.lock_running:
            try:
                msg = apply_engine(self.core_list())
                if not self.silent_var.get():
                    self.log(msg)
            except Exception as e:
                if not self.silent_var.get():
                    self.log(f"Guard fout: {e}")
            time.sleep(1.0)

    def magic_start(self):
        self.save()
        self.log("MAGIC START: engine wordt gestart...")
        if not is_admin():
            self.log("Let op: start als Administrator voor maximale werking.")

        self.log(set_power_mode())
        if self.gpu_var.get():
            self.log(gpu_preference(self.path_var.get()))
        if self.network_var.get():
            self.log(network_fix())
        self.log(trim_ram())
        if self.overlay_var.get():
            self.log(quiet_overlays())
        self.log(input_boost())

        self.log(self.launch_gameloop())
        time.sleep(2)
        self.log(apply_engine(self.core_list()))

        if self.guard_var.get():
            self.start_guard()

        self.log("MAGIC START KLAAR: CPU affinity, priority, power, GPU, spike clean en Ultra Mode actief.")

    def simple_page(self, heading, sub, actions):
        self.clear()
        self.title(heading, sub)
        c = self.card(self.content, heading)
        c.pack(fill="both", expand=True, padx=30, pady=16)
        self.logbox = tk.Text(c, height=14, bg="#030603", fg=MUTED, insertbackground=WHITE, relief="flat", font=("Consolas", 10))
        self.logbox.pack(side="bottom", fill="both", expand=True, padx=16, pady=16)
        for label, cmd, color in actions:
            GlowButton(c, text=label, command=lambda cm=cmd: self.log(cm()), bg=color, font=("Segoe UI", 14, "bold"), pady=12).pack(fill="x", padx=16, pady=8)

    def show_ram(self):
        self.simple_page("RAM CLEANER", "Spike clean tegen stutter en tijdelijke RAM-rommel.", [("🧹 RUN SPIKE CLEAN", trim_ram, "#08a51b")])

    def show_net(self):
        self.simple_page("CONNECTIVITY FIX", "DNS flush en stabiele TCP gaming defaults.", [("🌐 APPLY NETWORK STABILITY", network_fix, "#08a51b")])

    def show_pc(self):
        self.simple_page("PC OPTIMIZE", "Power mode, GPU preference en overlay priority.", [
            ("⚡ POWER MODE", set_power_mode, "#08a51b"),
            ("🎮 GPU HIGH PERFORMANCE", lambda: gpu_preference(self.path_var.get()), "#08a51b"),
            ("🔕 QUIET OVERLAYS/JUNK", quiet_overlays, "#08a51b"),
        ])

    def show_fps(self):
        self.simple_page("FPS BOOST", "Lock GameLoop/AOW elke 1 seconde op cores en high priority.", [
            ("🎮 APPLY ENGINE ONCE", lambda: apply_engine(self.core_list()), "#08a51b"),
            ("🛡 START FPS DROP GUARD", lambda: (self.start_guard() or "Guard gestart"), "#08a51b"),
            ("⛔ STOP FPS DROP GUARD", lambda: (self.stop_guard() or "Guard gestopt"), "#9b0000"),
        ])

    def show_input(self):
        self.simple_page("SENSITIVITY / INPUT BOOST", "Mouse acceleration uit voor strakkere input.", [("🖱 MOUSE & KEYBOARD BOOST", input_boost, "#08a51b")])

    def show_engine(self):
        self.show_home()

    def monitor_loop(self):
        while self.monitor_running:
            if psutil:
                try:
                    cpu = psutil.cpu_percent(interval=0.2)
                    ram = psutil.virtual_memory().percent
                    def update():
                        if hasattr(self, "cpu_bar"):
                            self.cpu_bar["value"] = cpu
                            self.ram_bar["value"] = ram
                            self.cpu_label.config(text=f"CPU: {cpu:.0f}%")
                            self.ram_label.config(text=f"RAM: {ram:.0f}%")
                    self.after(0, update)
                except Exception:
                    pass
            time.sleep(1)

if __name__ == "__main__":
    ProApp().mainloop()
