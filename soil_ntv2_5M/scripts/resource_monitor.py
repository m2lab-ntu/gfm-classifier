#!/usr/bin/env python3
"""
Resource monitoring utilities for tracking GPU, RAM, and time usage.

Designed for HPC environments (SLURM) to help evaluate whether
compute resources are sufficient or need upgrading.

Usage:
    monitor = ResourceMonitor(device="cuda:0")
    monitor.start()
    ...
    monitor.epoch_start(epoch=1)
    # training loop
    monitor.epoch_end(epoch=1, train_samples=4500000)
    ...
    monitor.stop()
    monitor.save_report("results/resource_report.json")
    monitor.print_summary()
"""

import json
import os
import platform
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import psutil
import torch


def _bytes_to_gb(b: int) -> float:
    return b / (1024 ** 3)


def _nvidia_smi_query() -> Optional[Dict]:
    """Query nvidia-smi for GPU utilization and memory (independent of PyTorch)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        lines = result.stdout.strip().split("\n")
        if not lines:
            return None
        parts = [p.strip() for p in lines[0].split(",")]
        return {
            "gpu_utilization_pct": float(parts[0]),
            "gpu_memory_used_mb": float(parts[1]),
            "gpu_memory_total_mb": float(parts[2]),
            "gpu_temperature_c": float(parts[3]),
            "gpu_power_w": float(parts[4]) if parts[4] != "[N/A]" else None,
        }
    except Exception:
        return None


class ResourceMonitor:
    """Tracks GPU, RAM, and time resources throughout training/evaluation."""

    def __init__(self, device: str = "cuda:0", sample_interval: float = 10.0):
        """
        Args:
            device: CUDA device string.
            sample_interval: Seconds between background GPU/RAM sampling.
        """
        self.device = device
        self.sample_interval = sample_interval

        self.process = psutil.Process(os.getpid())
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None

        # Per-epoch tracking
        self._epoch_starts: Dict[int, float] = {}
        self._epoch_durations: Dict[int, float] = {}
        self._epoch_samples: Dict[int, int] = {}

        # Background sampling data
        self._samples: List[Dict] = []
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Peak tracking
        self._peak_ram_bytes = 0
        self._peak_gpu_mem_mb = 0.0
        self._gpu_util_samples: List[float] = []

        # System info
        self._system_info = self._collect_system_info()

    def _collect_system_info(self) -> Dict:
        info = {
            "hostname": platform.node(),
            "os": platform.platform(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "ram_total_gb": round(_bytes_to_gb(psutil.virtual_memory().total), 2),
        }
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info.update({
                "gpu_name": props.name,
                "gpu_vram_total_gb": round(props.total_memory / (1024 ** 3), 2),
                "gpu_compute_capability": f"{props.major}.{props.minor}",
                "cuda_version": torch.version.cuda or "N/A",
                "pytorch_version": torch.__version__,
            })
        return info

    def _background_sampler(self):
        """Background thread that periodically samples GPU and RAM usage."""
        while not self._stop_event.is_set():
            sample = {"timestamp": time.time()}

            # RAM
            mem = self.process.memory_info()
            sample["ram_rss_gb"] = round(_bytes_to_gb(mem.rss), 3)
            sample["ram_vms_gb"] = round(_bytes_to_gb(mem.vms), 3)
            self._peak_ram_bytes = max(self._peak_ram_bytes, mem.rss)

            # System-wide RAM
            vm = psutil.virtual_memory()
            sample["system_ram_used_pct"] = vm.percent
            sample["system_ram_available_gb"] = round(_bytes_to_gb(vm.available), 2)

            # GPU via nvidia-smi
            gpu_info = _nvidia_smi_query()
            if gpu_info:
                sample.update(gpu_info)
                self._peak_gpu_mem_mb = max(self._peak_gpu_mem_mb, gpu_info["gpu_memory_used_mb"])
                if gpu_info["gpu_utilization_pct"] is not None:
                    self._gpu_util_samples.append(gpu_info["gpu_utilization_pct"])

            # GPU via PyTorch
            if torch.cuda.is_available():
                sample["torch_gpu_allocated_gb"] = round(
                    torch.cuda.memory_allocated() / (1024 ** 3), 3
                )
                sample["torch_gpu_reserved_gb"] = round(
                    torch.cuda.memory_reserved() / (1024 ** 3), 3
                )
                sample["torch_gpu_max_allocated_gb"] = round(
                    torch.cuda.max_memory_allocated() / (1024 ** 3), 3
                )

            self._samples.append(sample)
            self._stop_event.wait(self.sample_interval)

    def start(self):
        """Start monitoring (call before training/eval begins)."""
        self._start_time = time.time()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        self._stop_event.clear()
        self._sampling_thread = threading.Thread(target=self._background_sampler, daemon=True)
        self._sampling_thread.start()
        print(f"[ResourceMonitor] Started (sampling every {self.sample_interval}s)")

    def stop(self):
        """Stop monitoring."""
        self._stop_time = time.time()
        self._stop_event.set()
        if self._sampling_thread:
            self._sampling_thread.join(timeout=5)
        print(f"[ResourceMonitor] Stopped ({len(self._samples)} samples collected)")

    def epoch_start(self, epoch: int):
        """Mark start of an epoch."""
        self._epoch_starts[epoch] = time.time()

    def epoch_end(self, epoch: int, train_samples: int = 0):
        """Mark end of an epoch and record throughput."""
        if epoch in self._epoch_starts:
            duration = time.time() - self._epoch_starts[epoch]
            self._epoch_durations[epoch] = duration
            self._epoch_samples[epoch] = train_samples

    def get_epoch_throughput(self, epoch: int) -> float:
        """Get reads/sec for a specific epoch."""
        duration = self._epoch_durations.get(epoch, 0)
        samples = self._epoch_samples.get(epoch, 0)
        return samples / duration if duration > 0 else 0

    def snapshot(self) -> Dict:
        """Take a single point-in-time snapshot (for inline logging)."""
        snap = {}
        mem = self.process.memory_info()
        snap["ram_rss_gb"] = round(_bytes_to_gb(mem.rss), 2)

        if torch.cuda.is_available():
            snap["gpu_allocated_gb"] = round(torch.cuda.memory_allocated() / (1024 ** 3), 2)
            snap["gpu_max_allocated_gb"] = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 2)

        gpu_info = _nvidia_smi_query()
        if gpu_info:
            snap["gpu_util_pct"] = gpu_info["gpu_utilization_pct"]
            snap["gpu_mem_used_mb"] = gpu_info["gpu_memory_used_mb"]
            snap["gpu_temp_c"] = gpu_info["gpu_temperature_c"]
            snap["gpu_power_w"] = gpu_info["gpu_power_w"]

        return snap

    def build_report(self) -> Dict:
        """Build full resource usage report."""
        total_time = (self._stop_time or time.time()) - (self._start_time or time.time())

        # Aggregate GPU utilization stats
        gpu_util_stats = {}
        if self._gpu_util_samples:
            import numpy as np
            arr = np.array(self._gpu_util_samples)
            gpu_util_stats = {
                "gpu_utilization_mean_pct": round(float(arr.mean()), 1),
                "gpu_utilization_median_pct": round(float(np.median(arr)), 1),
                "gpu_utilization_min_pct": round(float(arr.min()), 1),
                "gpu_utilization_max_pct": round(float(arr.max()), 1),
                "gpu_utilization_std_pct": round(float(arr.std()), 1),
            }

        # RAM stats
        ram_samples = [s.get("ram_rss_gb", 0) for s in self._samples if "ram_rss_gb" in s]
        ram_stats = {}
        if ram_samples:
            import numpy as np
            arr = np.array(ram_samples)
            ram_stats = {
                "ram_rss_mean_gb": round(float(arr.mean()), 2),
                "ram_rss_max_gb": round(float(arr.max()), 2),
                "ram_rss_min_gb": round(float(arr.min()), 2),
            }

        # Per-epoch timing
        epoch_stats = []
        for ep in sorted(self._epoch_durations.keys()):
            dur = self._epoch_durations[ep]
            samples = self._epoch_samples.get(ep, 0)
            epoch_stats.append({
                "epoch": ep,
                "duration_sec": round(dur, 1),
                "duration_str": str(timedelta(seconds=int(dur))),
                "train_samples": samples,
                "throughput_reads_per_sec": round(samples / dur, 1) if dur > 0 and samples > 0 else None,
            })

        # PyTorch peak GPU memory
        pytorch_peak_gb = 0.0
        if torch.cuda.is_available():
            pytorch_peak_gb = round(torch.cuda.max_memory_allocated() / (1024 ** 3), 2)

        report = {
            "system_info": self._system_info,
            "timing": {
                "total_wall_time_sec": round(total_time, 1),
                "total_wall_time_str": str(timedelta(seconds=int(total_time))),
                "start": datetime.fromtimestamp(self._start_time).isoformat() if self._start_time else None,
                "end": datetime.fromtimestamp(self._stop_time).isoformat() if self._stop_time else None,
                "num_epochs": len(self._epoch_durations),
                "avg_epoch_sec": round(sum(self._epoch_durations.values()) / len(self._epoch_durations), 1) if self._epoch_durations else None,
            },
            "gpu_memory": {
                "pytorch_peak_allocated_gb": pytorch_peak_gb,
                "nvidia_smi_peak_used_mb": round(self._peak_gpu_mem_mb, 0),
                "nvidia_smi_peak_used_gb": round(self._peak_gpu_mem_mb / 1024, 2),
                "vram_total_gb": self._system_info.get("gpu_vram_total_gb", None),
                "vram_utilization_pct": round(
                    (self._peak_gpu_mem_mb / 1024) / self._system_info.get("gpu_vram_total_gb", 1) * 100, 1
                ) if self._system_info.get("gpu_vram_total_gb") else None,
            },
            "gpu_compute": gpu_util_stats,
            "ram": {
                **ram_stats,
                "peak_rss_gb": round(_bytes_to_gb(self._peak_ram_bytes), 2),
                "system_total_gb": self._system_info.get("ram_total_gb", None),
                "ram_utilization_pct": round(
                    _bytes_to_gb(self._peak_ram_bytes) / self._system_info.get("ram_total_gb", 1) * 100, 1
                ) if self._system_info.get("ram_total_gb") else None,
            },
            "epoch_details": epoch_stats,
            "sampling": {
                "interval_sec": self.sample_interval,
                "total_snapshots": len(self._samples),
            },
        }
        return report

    def save_report(self, path: str):
        """Save resource usage report to JSON."""
        report = self.build_report()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[ResourceMonitor] Report saved to {path}")

    def print_summary(self):
        """Print concise resource usage summary to stdout."""
        report = self.build_report()

        print(f"\n{'=' * 70}")
        print("RESOURCE USAGE SUMMARY")
        print(f"{'=' * 70}")

        # System info
        si = report["system_info"]
        print(f"\n  System:")
        print(f"    Host:        {si.get('hostname', 'N/A')}")
        print(f"    CPU:         {si.get('cpu_count_physical', '?')} cores "
              f"({si.get('cpu_count_logical', '?')} logical)")
        print(f"    RAM:         {si.get('ram_total_gb', '?')} GB total")
        print(f"    GPU:         {si.get('gpu_name', 'N/A')}")
        print(f"    VRAM:        {si.get('gpu_vram_total_gb', '?')} GB")
        print(f"    CUDA:        {si.get('cuda_version', 'N/A')}")
        print(f"    PyTorch:     {si.get('pytorch_version', 'N/A')}")

        # Timing
        t = report["timing"]
        print(f"\n  Timing:")
        print(f"    Total wall time:  {t['total_wall_time_str']}")
        if t.get("avg_epoch_sec"):
            print(f"    Avg epoch time:   {timedelta(seconds=int(t['avg_epoch_sec']))}")
            print(f"    Epochs completed: {t['num_epochs']}")

        # GPU Memory
        gm = report["gpu_memory"]
        print(f"\n  GPU Memory (VRAM):")
        print(f"    PyTorch peak allocated: {gm['pytorch_peak_allocated_gb']:.2f} GB")
        print(f"    nvidia-smi peak used:   {gm['nvidia_smi_peak_used_gb']:.2f} GB")
        print(f"    VRAM total:             {gm.get('vram_total_gb', '?')} GB")
        if gm.get("vram_utilization_pct"):
            print(f"    VRAM utilization:       {gm['vram_utilization_pct']:.1f}%")

        # GPU Compute
        gc = report["gpu_compute"]
        if gc:
            print(f"\n  GPU Compute Utilization:")
            print(f"    Mean:   {gc.get('gpu_utilization_mean_pct', '?')}%")
            print(f"    Median: {gc.get('gpu_utilization_median_pct', '?')}%")
            print(f"    Min:    {gc.get('gpu_utilization_min_pct', '?')}%")
            print(f"    Max:    {gc.get('gpu_utilization_max_pct', '?')}%")

        # RAM
        r = report["ram"]
        print(f"\n  System RAM:")
        print(f"    Peak RSS:       {r.get('peak_rss_gb', '?')} GB")
        print(f"    Mean RSS:       {r.get('ram_rss_mean_gb', '?')} GB")
        print(f"    System total:   {r.get('system_total_gb', '?')} GB")
        if r.get("ram_utilization_pct"):
            print(f"    RAM utilization: {r['ram_utilization_pct']:.1f}%")

        # Per-epoch throughput
        epochs = report["epoch_details"]
        if epochs:
            print(f"\n  Per-epoch throughput:")
            print(f"    {'Epoch':<8} {'Duration':<12} {'Samples':<12} {'Reads/sec':<12}")
            print(f"    {'-'*8} {'-'*12} {'-'*12} {'-'*12}")
            for e in epochs[-5:]:  # show last 5 epochs
                tp = e.get("throughput_reads_per_sec")
                tp_str = f"{tp:,.1f}" if tp else "N/A"
                print(f"    {e['epoch']:<8} {e['duration_str']:<12} "
                      f"{e.get('train_samples', 0):>10,}  {tp_str:>10}")

        # Capacity assessment
        print(f"\n  Capacity Assessment:")
        vram_pct = gm.get("vram_utilization_pct", 0)
        ram_pct = r.get("ram_utilization_pct", 0)

        if vram_pct > 90:
            print(f"    VRAM:  CRITICAL ({vram_pct:.0f}%) — risk of OOM, consider reducing batch size or model size")
        elif vram_pct > 70:
            print(f"    VRAM:  HIGH ({vram_pct:.0f}%) — close to limit, limited room for scaling")
        elif vram_pct > 40:
            print(f"    VRAM:  MODERATE ({vram_pct:.0f}%) — room to increase batch size")
        else:
            print(f"    VRAM:  LOW ({vram_pct:.0f}%) — significant headroom, can increase batch size substantially")

        if ram_pct > 80:
            print(f"    RAM:   HIGH ({ram_pct:.0f}%) — may need more memory for larger datasets")
        elif ram_pct > 50:
            print(f"    RAM:   MODERATE ({ram_pct:.0f}%) — acceptable")
        else:
            print(f"    RAM:   LOW ({ram_pct:.0f}%) — plenty of headroom")

        gpu_mean = gc.get("gpu_utilization_mean_pct", 0)
        if gpu_mean > 80:
            print(f"    GPU compute: WELL UTILIZED ({gpu_mean:.0f}%) — good")
        elif gpu_mean > 50:
            print(f"    GPU compute: MODERATE ({gpu_mean:.0f}%) — could improve with larger batch size")
        else:
            print(f"    GPU compute: UNDERUTILIZED ({gpu_mean:.0f}%) — increase batch size or reduce data loading bottleneck")

        print(f"{'=' * 70}\n")
