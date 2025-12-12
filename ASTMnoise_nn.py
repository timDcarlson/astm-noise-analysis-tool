"""
ASTM Noise Analysis - Neural Network Characterization

This script mirrors the existing file handling (selection, discovery, ordering, per-file loading)
and adds a lightweight Fourier-feature MLP to denoise and characterize trends in the Main and
Reference channels. It does not replace ASTMnoise.py; it is an additional analysis tool.

Usage (from the project folder):
    # Heuristic-only (no NN training, recommended for speed/robustness)
    py ASTMnoise_nn.py --no-nn

    # With optional NN smoothing
    py ASTMnoise_nn.py [--use-nn] [--epochs 800] [--lr 0.005] [--n-freq 16] [--hidden 64]
                       [--patience 80] [--min-delta 1e-4]
                       [--save-model model.pth] [--load-model model.pth]

Outputs (written next to the data files):
    - nn_analysis_summary.csv    : channel-level trend metrics
    - nn_denoised_main.csv       : time, original, processed, residual for Main (processed = raw if --no-nn)
    - nn_denoised_reference.csv  : same for Reference
    - nn_model_main.pth / nn_model_ref.pth : per-channel trained weights (only if --use-nn)

Requirements:
    - torch (PyTorch) must be installed; if missing, the script will print a clear error.
"""

import os
import glob
import re
import math
import csv
import argparse
import numpy as np
import sys
import json
import tkinter as tk
from tkinter import filedialog

try:
    import torch
    import torch.nn as nn
except ImportError as exc:
    raise SystemExit(
        "PyTorch is required for ASTMnoise_nn.py. Install with `pip install torch` (CPU-only is fine).\n"
        f"Original error: {exc}"
    )

# -------------------------------
# File discovery and loading
# -------------------------------

def extract_timestamp(filename: str) -> str:
    basename = os.path.basename(filename)
    match = re.match(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", basename)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-\d{2}-\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2})", basename)
    if match:
        return match.group(1)
    return basename


def discover_files(first_filepath: str):
    folder = os.path.dirname(first_filepath)
    patterns = [
        os.path.join(folder, "*_*_DataCollection.txt"),
        os.path.join(folder, "*.txt"),
    ]
    all_files = []
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            all_files = files
            break
    all_files.sort(key=extract_timestamp)

    files_to_process = [first_filepath]
    selected_ts = extract_timestamp(os.path.basename(first_filepath))
    for fp in all_files:
        if fp == first_filepath:
            continue
        if extract_timestamp(os.path.basename(fp)) > selected_ts:
            files_to_process.append(fp)
    return files_to_process


def load_files(files):
    """Load data, stitch times with offsets, return dict with arrays."""
    raw = {
        "time": [],
        "main": [],
        "ref": [],
    }
    time_offset = 0.0
    for idx, fp in enumerate(files):
        data = np.loadtxt(fp, delimiter="\t", skiprows=2)
        times = data[:, 0]
        offset_times = times + time_offset
        raw["time"].extend(offset_times)
        raw["main"].extend(data[:, 2])
        raw["ref"].extend(data[:, 4])
        time_offset = offset_times[-1]
    # Convert to numpy arrays
    raw["time"] = np.asarray(raw["time"], dtype=np.float32)
    raw["main"] = np.asarray(raw["main"], dtype=np.float32)
    raw["ref"] = np.asarray(raw["ref"], dtype=np.float32)
    return raw

# -------------------------------
# Fourier-feature MLP
# -------------------------------

class FourierFeatures(nn.Module):
    def __init__(self, n_freq: int = 16):
        super().__init__()
        self.n_freq = n_freq
        freqs = torch.arange(1, n_freq + 1).float()
        self.register_buffer("freqs", freqs)

    def forward(self, t: torch.Tensor):
        # t is shape [N, 1], normalized 0..1
        angles = 2 * math.pi * t * self.freqs  # broadcast over freq
        sin = torch.sin(angles)
        cos = torch.cos(angles)
        return torch.cat([t, sin, cos], dim=-1)


class FourierMLP(nn.Module):
    def __init__(self, n_freq: int = 16, hidden: int = 64):
        super().__init__()
        in_dim = 1 + 2 * n_freq
        self.ff = FourierFeatures(n_freq)
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, t: torch.Tensor):
        x = self.ff(t)
        return self.net(x)


class ConvDenoiser(nn.Module):
    """Small 1D conv net for edge/spike sensitivity."""

    def __init__(self, channels: int = 32):
        super().__init__()
        def pad(kernel: int, dilation: int = 1) -> int:
            return ((kernel - 1) * dilation) // 2

        self.net = nn.Sequential(
            nn.Conv1d(1, channels, kernel_size=5, padding=pad(5)),
            nn.ReLU(),
            nn.Conv1d(channels, channels, kernel_size=5, padding=pad(5, dilation=2), dilation=2),
            nn.ReLU(),
            nn.Conv1d(channels, 1, kernel_size=5, padding=pad(5)),
        )

    def forward(self, x: torch.Tensor):
        return self.net(x)


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def fit_model(
    times: np.ndarray,
    values: np.ndarray,
    n_freq: int = 256,
    hidden: int = 32,
    epochs: int = 4000,
    lr: float = 1e-4,
    patience: int = 80,
    min_delta: float = 1e-6,
    save_model_path: str | None = None,
    load_model_path: str | None = None,
    model_type: str = "fourier",
    normalize_y: bool = True,
    device: torch.device | None = None,
):
    device = device or get_device()
    t_min, t_max = times.min(), times.max()
    if t_max - t_min < 1e-9:
        t_max = t_min + 1.0
    t_norm = (times - t_min) / (t_max - t_min)
    t_tensor = torch.from_numpy(t_norm).float().view(-1, 1).to(device)
    y_np = values.astype(np.float32)
    if normalize_y:
        y_mean = float(np.mean(y_np))
        y_std = float(np.std(y_np) + 1e-9)
        y_work = (y_np - y_mean) / y_std
    else:
        y_mean, y_std = 0.0, 1.0
        y_work = y_np
    y_tensor = torch.from_numpy(y_work).float().view(-1, 1).to(device)
    if model_type == "conv":
        model = ConvDenoiser(channels=hidden).to(device)
        loss_fn = nn.MSELoss()
        x_seq = torch.from_numpy(y_work).float().view(1, 1, -1).to(device)
        target_seq = x_seq
        if load_model_path and os.path.exists(load_model_path):
            state = torch.load(load_model_path, map_location=device)
            model.load_state_dict(state)
        else:
            opt = torch.optim.Adam(model.parameters(), lr=lr)
            best_loss = float("inf")
            stale = 0
            model.train()
            for _ in range(epochs):
                opt.zero_grad()
                pred = model(x_seq)
                loss = loss_fn(pred, target_seq)
                loss.backward()
                opt.step()

                loss_val = loss.item()
                if loss_val < best_loss - min_delta:
                    best_loss = loss_val
                    stale = 0
                else:
                    stale += 1
                    if stale >= patience:
                        break

            if save_model_path:
                torch.save(model.state_dict(), save_model_path)

        model.eval()
        with torch.no_grad():
            pred_norm = model(x_seq).cpu().squeeze().numpy()
    else:
        model = FourierMLP(n_freq=n_freq, hidden=hidden).to(device)
        loss_fn = nn.MSELoss()

        # If a model is provided, load and skip training
        if load_model_path and os.path.exists(load_model_path):
            state = torch.load(load_model_path, map_location=device)
            model.load_state_dict(state)
        else:
            opt = torch.optim.Adam(model.parameters(), lr=lr)
            best_loss = float("inf")
            stale = 0
            model.train()
            for _ in range(epochs):
                opt.zero_grad()
                pred = model(t_tensor)
                loss = loss_fn(pred, y_tensor)
                loss.backward()
                opt.step()

                loss_val = loss.item()
                if loss_val < best_loss - min_delta:
                    best_loss = loss_val
                    stale = 0
                else:
                    stale += 1
                    if stale >= patience:
                        break

            if save_model_path:
                torch.save(model.state_dict(), save_model_path)

        model.eval()
        with torch.no_grad():
            pred_norm = model(t_tensor).cpu().squeeze().numpy()

    denoised = pred_norm * y_std + y_mean
    return denoised

# -------------------------------
# Trend analysis heuristics
# -------------------------------

def _local_zscore(signal: np.ndarray, window_samples: int):
    if window_samples <= 0 or signal.size == 0:
        return np.zeros_like(signal)

    window_samples = min(window_samples, signal.size)
    weights = np.ones(window_samples, dtype=float)
    mean = np.convolve(signal, weights, mode="same") / window_samples
    sq_mean = np.convolve(signal * signal, weights, mode="same") / window_samples
    var = np.clip(sq_mean - mean * mean, 1e-12, None)
    std = np.sqrt(var)
    return (signal - mean) / (std + 1e-9)


def _logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _gaussian_template(length: int) -> np.ndarray:
    if length <= 0:
        return np.zeros(1)
    x = np.linspace(-1.0, 1.0, length)
    template = np.exp(-0.5 * (x / 0.3) ** 2)
    return template


def _template_score(segment: np.ndarray, template: np.ndarray) -> float:
    if segment.size == 0 or template.size == 0:
        return 0.0
    seg = segment - segment.mean()
    templ = template - template.mean()
    denom = np.linalg.norm(seg) * np.linalg.norm(templ)
    if denom <= 0:
        return 0.0
    return float(np.dot(seg, templ) / denom)


def detect_bell_curve_events(times: np.ndarray, signal: np.ndarray, min_amplitude: float = 0.5, min_width: float = 1.0, min_probability: float = 0.5) -> list[dict]:
    if signal.size == 0:
        return []

    duration = float(times[-1] - times[0]) if len(times) > 1 else 0.0
    dt_mean = float(np.mean(np.diff(times))) if len(times) > 1 else 1.0
    min_amplitude = max(float(min_amplitude), 0.0)
    min_width = max(float(min_width), 0.01)
    min_probability = min(max(float(min_probability), 0.0), 1.0)
    width_options = [0.5, 1.0, 2.0, 4.0]
    if min_width not in width_options:
        width_options.append(min_width)
    width_options = sorted(set(width_options))
    max_allowed = max(1.0, duration)
    width_seconds = [w for w in width_options if w <= max_allowed]
    mask = np.zeros(signal.shape, dtype=bool)
    events: list[dict] = []

    for width in width_seconds:
        win_samples = max(3, int(round(width / (dt_mean + 1e-9))))
        if win_samples >= len(signal):
            win_samples = len(signal)
        step = max(1, win_samples // 3)
        tmpl = _gaussian_template(win_samples)
        for start in range(0, len(signal) - win_samples + 1, step):
            end = start + win_samples
            if mask[start:end].any():
                continue
            segment = signal[start:end]
            score_pos = _template_score(segment, tmpl)
            score_neg = _template_score(-segment, tmpl)
            orientation = 1 if score_pos >= score_neg else -1
            score = score_pos if orientation == 1 else score_neg
            prob = _logistic((score - 0.65) * 6.0)
            if prob <= 0.5:
                continue
            if prob < min_probability:
                continue
            baseline = float(np.median(segment))
            if orientation == 1:
                amplitude = float(np.max(segment) - baseline)
            else:
                amplitude = float(baseline - np.min(segment))
            amplitude = max(amplitude, 0.0)
            if amplitude < min_amplitude:
                continue
            actual_width = float(times[end - 1] - times[start]) if end - start > 1 else float(width)
            if actual_width < min_width:
                continue
            events.append({
                "start": float(times[start]),
                "end": float(times[end - 1]),
                "prob": float(prob),
                "orientation": orientation,
                "width_s": float(actual_width),
                "amplitude": float(amplitude),
            })
            mask[start:end] = True
    return events


def summarize_trends(times: np.ndarray, signal: np.ndarray, events: list[dict] | None = None):
    dt = np.gradient(times)
    dy = np.gradient(signal)
    slope = dy / (dt + 1e-9)
    duration = float(times[-1] - times[0]) if len(times) > 1 else 0.0

    # Early window (first 30s) statistics
    t0 = times[0]
    early_mask = (times - t0) <= 30.0
    early_signal = signal[early_mask] if np.any(early_mask) else signal[:1]
    early_dt = np.diff(times[early_mask]) if np.sum(early_mask) > 1 else np.array([1.0])
    early_dt_mean = float(np.mean(early_dt)) if early_dt.size else 1.0
    start_intensity_raw = float(np.mean(early_signal))
    start_intensity_scaled = start_intensity_raw / (early_dt_mean + 1e-9)

    end_intensity = float(signal[-1])
    mean_intensity = float(np.mean(signal))
    signal_std = float(np.std(signal))
    signal_range = float(np.max(signal) - np.min(signal))
    sig_std_eps = signal_std + 1e-9

    p95_pos_slope = float(np.percentile(slope, 95))
    p05_neg_slope = float(np.percentile(slope, 5))
    events = events if events is not None else detect_bell_curve_events(times, signal)
    event_probs = [ev["prob"] for ev in events]
    event_count = len(events)
    duration_hr = max(1.0 / 3600.0, duration / 3600.0)
    bell_events_per_hour = event_count / duration_hr
    mean_prob = float(np.mean(event_probs)) if event_probs else 0.0

    # Flat regions: sliding window std below small fraction of global std
    flat_windows = 0
    win = 200 if len(signal) >= 200 else max(20, len(signal) // 5)
    if win > 0 and win < len(signal):
        rolling_std = np.array([
            np.std(signal[i:i + win])
            for i in range(0, len(signal) - win, win // 2)
        ])
        flat_windows = int(np.sum(rolling_std < 0.01 * sig_std_eps))

    # Steep segments: slope beyond 3x std
    slope_std = float(np.std(slope) + 1e-9)
    steep_segments = int(np.sum(np.abs(slope) > 3.0 * slope_std))

    # Discontinuities: large jumps between consecutive points
    jumps = np.abs(np.diff(signal))
    jump_thresh = np.percentile(jumps, 99) if len(jumps) else 0.0
    discontinuities = int(np.sum(jumps > jump_thresh)) if jump_thresh > 0 else 0

    return {
        "start_intensity": start_intensity_raw,
        "start_intensity_scaled": start_intensity_scaled,
        "early_dt_mean": early_dt_mean,
        "end_intensity": end_intensity,
        "delta_intensity": end_intensity - start_intensity_raw,
        "mean_intensity": mean_intensity,
        "signal_std": signal_std,
        "signal_range": signal_range,
        "p95_pos_slope": p95_pos_slope,
        "p05_neg_slope": p05_neg_slope,
        "flat_windows": flat_windows,
        "steep_segments": steep_segments,
        "bell_curve_event_count": event_count,
        "bell_curve_events_per_hour": bell_events_per_hour,
        "bell_curve_mean_probability": mean_prob,
        "discontinuities": discontinuities,
    }

# -------------------------------
# Main flow
# -------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="NN denoising + trend extraction for ASTM data")
    parser.add_argument("--use-nn", action="store_true", help="Enable NN smoothing before heuristics")
    parser.add_argument("--no-nn", dest="use_nn", action="store_false", help="Disable NN smoothing (default)")
    parser.add_argument("--events-from-nn", dest="events_from_nn", action="store_true", default=True,
                        help="Compute bell-curve event metrics (flat/steep/discontinuities) on NN-denoised signal")
    parser.add_argument("--events-from-processed", dest="events_from_nn", action="store_false",
                        help="Compute event metrics on the same signal used for other metrics")
    parser.add_argument("--model", choices=["fourier", "conv"], default="fourier",
                        help="Backbone for NN smoothing: fourier-feature MLP or 1D conv")
    parser.add_argument("--file", type=str, default=None, help="Optional data file to process; skip file dialog if set")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directory where CSV outputs are written (default: folder containing the data file)")
    parser.add_argument("--epochs", type=int, default=4000, help="Max epochs")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--n-freq", type=int, default=256, help="Fourier feature count")
    parser.add_argument("--hidden", type=int, default=32, help="Hidden width")
    parser.add_argument("--patience", type=int, default=80, help="Early-stop patience (epochs)")
    parser.add_argument("--min-delta", type=float, default=1e-4, help="Early-stop improvement threshold")
    parser.add_argument("--min-event-amplitude", type=float, default=0.5,
                        help="Minimum amplitude for bell-curve events")
    parser.add_argument("--min-event-width", type=float, default=1.0,
                        help="Minimum bell-curve width (seconds) to consider")
    parser.add_argument("--min-event-probability", type=float, default=0.5,
                        help="Minimum bell-curve probability (0-1) to include")
    parser.add_argument("--save-model", type=str, default=None, help="Base path or directory to save trained weights; channel suffix is added (only if --use-nn)")
    parser.add_argument("--load-model", type=str, default=None, help="Path to load existing weights (skip training if found)")
    parser.set_defaults(use_nn=False)
    return parser.parse_args()


def main():
    # Match prior behavior: set working dir to script folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    args = parse_args()
    device = get_device()
    print(f"Using device: {device}")

    if args.file:
        first_file = os.path.abspath(args.file)
        if not os.path.isfile(first_file):
            print(f"File not found: {first_file}")
            return
    else:
        root = tk.Tk()
        root.withdraw()
        first_file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not first_file:
            print("No file selected. Exiting.")
            return

    files = discover_files(first_file)
    print(f"Starting with: {os.path.basename(first_file)}")
    print(f"Total files to process: {len(files)}")

    raw = load_files(files)
    total_span = float(raw["time"][-1] - raw["time"][0]) if len(raw["time"]) > 1 else 0.0
    if total_span < 30.0:
        print(f"Data span {total_span:.2f}s is shorter than the 30s window required to evaluate bell-curve events. Exiting.")
        sys.exit(1)

    # Output directory defaults to data folder but can be overridden
    if args.output_dir:
        out_dir = os.path.abspath(args.output_dir)
    else:
        out_dir = os.path.dirname(first_file)
    parent_name = os.path.basename(os.path.normpath(out_dir)) or "results"
    os.makedirs(out_dir, exist_ok=True)

    summaries = []
    outputs = {}
    event_details: dict[str, list[dict]] = {}
    for channel_key, label in [("main", "Main"), ("ref", "Reference")]:
        print(f"\nProcessing {label} channel ({len(raw[channel_key])} samples)...")

        processed = raw[channel_key]
        processed_nn = None

        if args.use_nn:
            # Determine per-channel save path
            if args.save_model:
                if os.path.isdir(args.save_model):
                    save_path = os.path.join(args.save_model, f"nn_model_{channel_key}.pth")
                else:
                    base, ext = os.path.splitext(args.save_model)
                    ext = ext or ".pth"
                    save_path = f"{base}_{channel_key}{ext}"
            else:
                save_path = os.path.join(out_dir, f"nn_model_{channel_key}.pth")

            load_path = args.load_model
            processed = fit_model(
                raw["time"],
                raw[channel_key],
                n_freq=args.n_freq,
                hidden=args.hidden,
                epochs=args.epochs,
                lr=args.lr,
                patience=args.patience,
                min_delta=args.min_delta,
                save_model_path=save_path,
                load_model_path=load_path,
                model_type=args.model,
                normalize_y=True,
                device=device,
            )

        # If events must come from NN but we didn't train for processed, train a lightweight NN here
        if args.events_from_nn:
            if processed is not raw[channel_key]:
                processed_nn = processed
            else:
                processed_nn = fit_model(
                    raw["time"],
                    raw[channel_key],
                    n_freq=args.n_freq,
                    hidden=args.hidden,
                    epochs=args.epochs,
                    lr=args.lr,
                    patience=args.patience,
                    min_delta=args.min_delta,
                    save_model_path=None,
                    load_model_path=None,
                    model_type=args.model,
                    normalize_y=True,
                    device=device,
                )
            event_signal = processed_nn if processed_nn is not None else processed
        else:
            processed_nn = processed
            event_signal = processed

        events = detect_bell_curve_events(
            raw["time"],
            event_signal,
            min_amplitude=args.min_event_amplitude,
            min_width=args.min_event_width,
            min_probability=args.min_event_probability,
        )
        summary = summarize_trends(raw["time"], processed, events=events)
        summary["channel"] = label
        summaries.append(summary)
        outputs[channel_key] = processed
        event_details[channel_key] = events

    # Write summaries to CSV next to data files
    summary_path = os.path.join(out_dir, f"{parent_name}_nn_analysis_summary.csv")
    fieldnames = [
        "channel",
        "start_intensity",
        "start_intensity_scaled",
        "early_dt_mean",
        "end_intensity",
        "delta_intensity",
        "mean_intensity",
        "signal_std",
        "signal_range",
        "p95_pos_slope",
        "p05_neg_slope",
        "flat_windows",
        "steep_segments",
        "bell_curve_event_count",
        "bell_curve_events_per_hour",
        "bell_curve_mean_probability",
        "discontinuities",
    ]
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, (int, np.integer)):
            return f"{v:.3e}"
        try:
            return f"{float(v):.3e}"
        except Exception:
            return v

    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            filtered = {k: fmt(row.get(k)) for k in fieldnames}
            writer.writerow(filtered)
    print(f"Summary written to {summary_path}")

    # Write denoised outputs for inspection
    for channel_key, den in outputs.items():
        out_path = os.path.join(out_dir, f"{parent_name}_nn_denoised_{channel_key}.csv")
        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time_s", "original", "processed", "residual"])
            for t, orig, dn in zip(raw["time"], raw[channel_key], den):
                writer.writerow([
                    f"{float(t):.3e}",
                    f"{float(orig):.3e}",
                    f"{float(dn):.3e}",
                    f"{float(orig - dn):.3e}",
                ])
        print(f"Denoised signal saved to {out_path}")

    for channel_key, events in event_details.items():
        event_path = os.path.join(out_dir, f"{parent_name}_nn_event_details_{channel_key}.json")
        try:
            with open(event_path, "w") as f:
                json.dump(events, f, indent=2)
            print(f"Event details saved to {event_path}")
        except Exception as exc:
            print(f"Failed to write event details for {channel_key}: {exc}")

    print("\nDone. Review the CSV outputs for trend metrics and denoised signals.")


if __name__ == "__main__":
    main()
