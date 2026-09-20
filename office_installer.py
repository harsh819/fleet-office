"""GUI wrapper around Microsoft's Office Deployment Tool (ODT)."""
import ctypes
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR = r"C:\MS Office"
SETUP_EXE = os.path.join(BASE_DIR, "setup.exe")
CONFIG_XML = os.path.join(BASE_DIR, "configuration.xml")
ERROR_LOG = os.path.join(BASE_DIR, "office_installer_error.log")

CREATE_NO_WINDOW = 0x08000000


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    params = " ".join(f'"{a}"' for a in sys.argv)
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, BASE_DIR, 1
    )
    # ShellExecuteW returns a value <= 32 on failure (e.g. 5 = user clicked "No")
    if ret <= 32:
        return False
    return True


def run_step(args) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )


APP_NAME = "FleetOffice"

COLOR_BG = "#f3f3f3"
COLOR_HEADER = "#1a3c6e"
COLOR_HEADER_TEXT = "#ffffff"
COLOR_ACCENT = "#0f6cbd"
COLOR_OK = "#0f7b0f"
COLOR_ERR = "#c42b1c"
COLOR_MUTED = "#5f6368"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)
        self.geometry("480x300")
        self.configure(bg=COLOR_BG)

        self._setup_style()

        header = tk.Frame(self, bg=COLOR_HEADER, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text=APP_NAME, bg=COLOR_HEADER, fg=COLOR_HEADER_TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=20, pady=(10, 0))
        tk.Label(
            header, text="Microsoft Office deployment", bg=COLOR_HEADER, fg="#cfe0f5",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20)

        body = tk.Frame(self, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        self.status_var = tk.StringVar(value="Checking prerequisites...")
        self.status_label = tk.Label(
            body, textvariable=self.status_var, bg=COLOR_BG, fg=COLOR_MUTED,
            font=("Segoe UI", 10), wraplength=420, justify="left",
        )
        self.status_label.pack(anchor="w", pady=(0, 16))

        self.progress = ttk.Progressbar(
            body, length=430, mode="determinate", maximum=2, style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(0, 24))

        self.start_btn = tk.Button(
            body, text="Start Installation", command=self.start,
            font=("Segoe UI", 10, "bold"), fg="#ffffff", bg=COLOR_ACCENT,
            activeforeground="#ffffff", activebackground="#0c5aa0",
            disabledforeground="#e0e0e0", relief="flat", bd=0,
            padx=18, pady=8, cursor="hand2",
        )
        self.start_btn.pack(anchor="e")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._running = False
        self.after(100, self.check_prereqs)

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use("clam")

        style.configure("TButton", font=("Segoe UI", 10), padding=(16, 8))
        style.configure(
            "Accent.TButton", font=("Segoe UI", 10, "bold"),
            padding=(16, 8), foreground="#ffffff", background=COLOR_ACCENT,
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", "#a0a0a0"), ("active", "#0c5aa0")],
            foreground=[("disabled", "#e0e0e0")],
        )
        style.configure(
            "Accent.Horizontal.TProgressbar", background=COLOR_ACCENT, troughcolor="#e2e2e2",
        )

    def check_prereqs(self):
        missing = []
        if not os.path.isfile(SETUP_EXE):
            missing.append("setup.exe")
        if not os.path.isfile(CONFIG_XML):
            missing.append("configuration.xml")
        if missing:
            self.status_label.configure(fg=COLOR_ERR)
            self.status_var.set(
                f"Missing required file(s) in {BASE_DIR}: {', '.join(missing)}. "
                f"Place both setup.exe and configuration.xml there before starting."
            )
            self.start_btn.configure(state="disabled")
        else:
            self.status_label.configure(fg=COLOR_MUTED)
            self.status_var.set(f"Ready to install Microsoft Office from {BASE_DIR}.")

    def start(self):
        if self._running:
            return
        self._running = True
        self.start_btn.configure(state="disabled")
        self.status_label.configure(fg=COLOR_MUTED)
        self.progress["value"] = 0
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        steps = [
            ("Downloading Office files...", [SETUP_EXE, "/download", CONFIG_XML]),
            ("Configuring / installing Office...", [SETUP_EXE, "/configure", CONFIG_XML]),
        ]
        for i, (label, args) in enumerate(steps):
            self.after(0, lambda l=label: self.status_var.set(l))
            try:
                result = run_step(args)
            except OSError as e:
                self.after(0, lambda e=e: self._fail(f"Failed to launch setup.exe: {e}", ""))
                return

            if result.returncode != 0:
                combined = (result.stdout or "") + "\n" + (result.stderr or "")
                self.after(0, lambda a=args, c=combined: self._fail(
                    f"Step failed (exit code {result.returncode}):\n{' '.join(a)}", c))
                return

            self.after(0, lambda v=i + 1: self.progress.configure(value=v))

        self.after(0, self._succeed)

    def _succeed(self):
        self._running = False
        self.status_label.configure(fg=COLOR_OK)
        self.status_var.set("Done.")
        self.start_btn.configure(state="normal")
        messagebox.showinfo("Success", "Microsoft Office Installed Successfully")

    def _fail(self, message, log_contents):
        self._running = False
        self.status_label.configure(fg=COLOR_ERR)
        self.status_var.set("Installation failed.")
        self.progress["value"] = 0
        self.start_btn.configure(state="normal")
        try:
            with open(ERROR_LOG, "w", encoding="utf-8") as f:
                f.write(log_contents)
        except OSError:
            pass
        messagebox.showerror(
            "Installation Failed",
            f"{message}\n\nDetails written to:\n{ERROR_LOG}",
        )

    def on_close(self):
        if self._running:
            if not messagebox.askyesno(
                "Installation in progress",
                "An installation is still running. Closing now may leave Office "
                "partially installed. Close anyway?",
            ):
                return
        self.destroy()


def main():
    if os.name != "nt":
        print("This tool only runs on Windows.")
        sys.exit(1)

    if not is_admin():
        if not relaunch_as_admin():
            messagebox.showerror(
                "Administrator rights required",
                "This installer needs to run as Administrator. Please approve "
                "the UAC prompt, or right-click and 'Run as administrator'.",
            )
        sys.exit(0)

    try:
        os.makedirs(BASE_DIR, exist_ok=True)
    except OSError as e:
        messagebox.showerror("Cannot create install folder", f"Failed to create {BASE_DIR}:\n{e}")
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
