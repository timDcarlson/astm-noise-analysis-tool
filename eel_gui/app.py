import csv
import os
import sys
import subprocess
import json
import eel
import tkinter as tk
from tkinter import filedialog

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "ASTMnoise_nn.py"))
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

eel.init(os.path.join(BASE_DIR, "web"))


def _bool_from_cfg(cfg, key, default=False):
    val = cfg.get(key, default)
    if isinstance(val, str):
        return val.lower() in {"1", "true", "yes", "on"}
    return bool(val)


def _float(cfg, key, default):
    try:
        return float(cfg.get(key, default))
    except Exception:
        return default


def _int(cfg, key, default):
    try:
        return int(cfg.get(key, default))
    except Exception:
        return default


@eel.expose
def run_analysis(cfg):
    """Build command line and run ASTMnoise_nn.py with provided options."""
    use_nn = _bool_from_cfg(cfg, "use_nn", False)
    # Events must come from NN; if use_nn is false, force Conv1d for events
    events_from_nn = True
    model = cfg.get("model", "fourier")
    if not use_nn:
        model = "conv"

    cmd = [sys.executable, SCRIPT_PATH]
    cmd.append("--use-nn" if use_nn else "--no-nn")
    cmd.append("--events-from-nn")
    cmd += ["--model", model]

    data_file = (cfg.get("file") or "").strip()
    out_dir = None
    if data_file:
        cmd += ["--file", data_file]
        out_dir = os.path.dirname(os.path.abspath(data_file))

    epochs = _int(cfg, "epochs", 4000)
    hidden = _int(cfg, "hidden", 256)
    n_freq = _int(cfg, "n_freq", 32)
    patience = _int(cfg, "patience", 80)
    lr = _float(cfg, "lr", 1e-6)
    min_delta = _float(cfg, "min_delta", 1e-6)
    min_event_amplitude = _float(cfg, "bell_min_amplitude", 0.5)
    min_event_width = _float(cfg, "bell_min_width", 1.0)
    raw_min_event_probability = _float(cfg, "bell_min_probability", 50.0)
    min_event_probability = max(0.0, min(100.0, raw_min_event_probability)) / 100.0

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        cmd += ["--output-dir", out_dir]
    cmd += ["--epochs", str(epochs)]
    cmd += ["--hidden", str(hidden)]
    cmd += ["--n-freq", str(n_freq)]
    cmd += ["--patience", str(patience)]
    cmd += ["--lr", str(lr)]
    cmd += ["--min-delta", str(min_delta)]
    cmd += ["--min-event-amplitude", str(min_event_amplitude)]
    cmd += ["--min-event-width", str(min_event_width)]
    cmd += ["--min-event-probability", str(min_event_probability)]

    load_model = (cfg.get("load_model") or "").strip()
    save_models = _bool_from_cfg(cfg, "save_models", False)
    if use_nn and save_models:
        cmd += ["--save-model", SCRIPT_DIR]
    if load_model:
        cmd += ["--load-model", load_model]

    try:
        proc = subprocess.run(
            cmd,
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        result = {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except Exception as exc:
        result = {
            "cmd": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
        }

    return json.dumps(result)


@eel.expose
def choose_file():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    root.destroy()
    return path or ""


@eel.expose
def choose_load_path():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(filetypes=[("PyTorch weights", "*.pth"), ("All files", "*.*")])
    root.destroy()
    return path or ""


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _read_denoised_csv(path):
    if not os.path.isfile(path):
        return None
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        data = {"time": [], "original": [], "processed": [], "residual": []}
        for row in reader:
            if len(row) < 4:
                continue
            try:
                data["time"].append(float(row[0]))
                data["original"].append(float(row[1]))
                data["processed"].append(float(row[2]))
                data["residual"].append(float(row[3]))
            except ValueError:
                continue
    return data


def _read_summary_stats(out_dir, prefix, channel_label):
    summary_path = os.path.join(out_dir, f"{prefix}_nn_analysis_summary.csv")
    if not os.path.isfile(summary_path):
        return {}
    with open(summary_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("channel", "").strip().lower() != channel_label.lower():
                continue
            return {
                "bell_curve_event_count": _safe_float(row.get("bell_curve_event_count")),
                "bell_curve_events_per_hour": _safe_float(row.get("bell_curve_events_per_hour")),
                "bell_curve_mean_probability": _safe_float(row.get("bell_curve_mean_probability")),
            }
    return {}


def _read_event_details(out_dir, prefix, channel_key):
    details_path = os.path.join(out_dir, f"{prefix}_nn_event_details_{channel_key}.json")
    if not os.path.isfile(details_path):
        return []
    try:
        with open(details_path, "r") as f:
            raw = json.load(f)
    except Exception:
        return []
    events = []
    for ev in raw:
        if not isinstance(ev, dict):
            continue
        events.append({
            "start": _safe_float(ev.get("start")),
            "end": _safe_float(ev.get("end")),
            "prob": _safe_float(ev.get("prob")),
            "width_s": _safe_float(ev.get("width_s")),
            "amplitude": _safe_float(ev.get("amplitude")),
            "orientation": ev.get("orientation"),
        })
    return events


@eel.expose
def load_denoised_data(data_file):
    if not data_file:
        return json.dumps({"main": None, "ref": None})
    out_dir = os.path.dirname(os.path.abspath(data_file))
    prefix = os.path.basename(os.path.normpath(out_dir)) or "results"

    def collect(kind, label):
        file_path = os.path.join(out_dir, f"{prefix}_nn_denoised_{kind}.csv")
        return {
            "series": _read_denoised_csv(file_path),
            "stats": _read_summary_stats(out_dir, prefix, label),
            "events": _read_event_details(out_dir, prefix, kind),
        }

    payload = {"main": collect("main", "Main"), "ref": collect("ref", "Reference")}
    return json.dumps(payload)


def main():
    # Use Firefox instead of Chrome/Chromium. Adjust the path if your install differs.
    firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"

    # Serve on a fixed port so we can pass the exact URL to Firefox.
    host = "localhost"
    port = 8888
    start_url = f"http://{host}:{port}/index.html"

    if not os.path.isfile(firefox_path):
        print("Firefox not found; start the app and open", start_url, "in your browser.")
        eel.start("index.html", mode=None, host=host, port=port, size=(1100, 900))
    else:
        eel.start(
            "index.html",
            mode="custom",
            cmdline_args=[firefox_path, "-new-window", start_url],
            host=host,
            port=port,
            size=(1100, 900),
        )


if __name__ == "__main__":
    main()
