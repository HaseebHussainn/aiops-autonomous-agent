from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict
import math


@dataclass
class RollingStats:
    n: int
    mean: float
    std: float


class RollingWindow:
    def __init__(self, window_size: int):
        if window_size < 5:
            raise ValueError("window_size must be >= 5")
        self.window_size = window_size
        self._buf: Dict[str, Deque[float]] = {}

    def push(self, metrics: Dict[str, float]) -> None:
        for k, v in metrics.items():
            if k not in self._buf:
                self._buf[k] = deque(maxlen=self.window_size)
            self._buf[k].append(float(v))

    def ready(self) -> bool:
        return bool(self._buf) and all(len(d) >= self.window_size for d in self._buf.values())

    def stats(self) -> Dict[str, RollingStats]:
        out: Dict[str, RollingStats] = {}
        for k, d in self._buf.items():
            vals = list(d)
            n = len(vals)
            if n == 0:
                continue
            mean = sum(vals) / n
            var = sum((x - mean) ** 2 for x in vals) / n
            std = math.sqrt(var)
            out[k] = RollingStats(n=n, mean=mean, std=std)
        return out

    def zscores(self, current: Dict[str, float], epsilon: float = 1e-6) -> Dict[str, float]:
        st = self.stats()
        z: Dict[str, float] = {}
        for k, x in current.items():
            if k not in st:
                continue
            denom = max(st[k].std, epsilon)
            z[k] = (float(x) - st[k].mean) / denom
        return z