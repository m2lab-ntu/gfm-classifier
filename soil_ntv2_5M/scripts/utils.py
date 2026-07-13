#!/usr/bin/env python3
"""Shared utilities for Token-level GFM Classifier."""

import json
import os
import time
from pathlib import Path

import numpy as np
import torch
import yaml


def load_config(config_path: str) -> dict:
    """Load YAML config file."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def save_config(cfg: dict, output_dir: str):
    """Save config to output directory."""
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "config.yaml"), "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)


def save_json(data: dict, path: str):
    """Save dict as JSON."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def count_parameters(model):
    """Count total and trainable parameters."""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total, trainable


class AverageMeter:
    """Track running average of a metric."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class EarlyStopping:
    """Early stopping based on validation metric."""

    def __init__(self, patience: int = 5, mode: str = "max"):
        self.patience = patience
        self.mode = mode
        self.best = None
        self.counter = 0
        self.should_stop = False

    def step(self, metric):
        if self.best is None:
            self.best = metric
            return True  # is_best

        if self.mode == "max":
            is_best = metric > self.best
        else:
            is_best = metric < self.best

        if is_best:
            self.best = metric
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True

        return is_best


class Timer:
    """Simple timer context manager."""

    def __init__(self):
        self.elapsed = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start

