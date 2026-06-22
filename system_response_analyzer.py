"""
پروژه ۴: نرم‌افزار تحلیل پاسخ سیستم‌های مرتبه اول و دوم
شماره دانشجویی: 03220040709006  |  a = 6
نام فایل: system_response_analyzer.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math

# ─────────────────────────────────────────
STUDENT_ID = "03220040709006"
A = 6
# ─────────────────────────────────────────


class TransferFunction:
    """تابع تبدیل سیستم مرتبه اول یا دوم"""

    def __init__(self, K: float, zeta: float = None, wn: float = None,
                 tau: float = None, order: int = 2):
        """
        order=1 : G(s) = K / (tau*s + 1)
        order=2 : G(s) = K*wn² / (s² + 2ζωn·s + ωn²)
        """
        self.K = K
        self.zeta = zeta
        self.wn = wn
        self.tau = tau
        self.order = order

    def __repr__(self):
        if self.order == 1:
            return f"G(s) = {self.K} / ({self.tau}s + 1)"
        else:
            return (f"G(s) = {self.K}·{self.wn:.3f}² / "
                    f"(s² + 2·{self.zeta:.3f}·{self.wn:.3f}·s + {self.wn:.3f}²)")


class StepResponse:
    """محاسبه پاسخ پله برای مرتبه اول یا دوم"""

    def __init__(self, tf: TransferFunction, t_end: float = 20.0, dt: float = 0.01):
        self.tf = tf
        self.t_end = t_end
        self.dt = dt
        self.time = []
        self.output = []

    def compute(self):
        self.time = []
        self.output = []
        tf = self.tf
        dt = self.dt
        t = 0.0

        if tf.order == 1:
            # y(t) = K·(1 - e^(-t/τ))
            while t <= self.t_end:
                y = tf.K * (1 - math.exp(-t / tf.tau)) if tf.tau > 0 else tf.K
                self.time.append(t)
                self.output.append(y)
                t += dt

        else:
            # حل عددی با روش اویلر:
            # ÿ + 2ζωnẏ + ωn²y = K·ωn²·u(t),  u(t)=1
            K, zeta, wn = tf.K, tf.zeta, tf.wn
            y, yd = 0.0, 0.0  # y و مشتق اول
            while t <= self.t_end:
                self.time.append(t)
                self.output.append(y)
                ydd = K * wn ** 2 - 2 * zeta * wn * yd - wn ** 2 * y
                yd += ydd * dt
                y += yd * dt
                t += dt

        return self.time, self.output


class Analyzer:
    """استخراج مشخصه‌های پاسخ پله"""

    def __init__(self, time: list, output: list, K: float):
        self.time = time
        self.output = output
        self.steady_state = K  # مقدار نهایی مطلوب

    def rise_time(self) -> float:
        """زمان صعود: 10% → 90% مقدار نهایی"""
        ss = self.steady_state
        t10 = t90 = None
        for t, y in zip(self.time, self.output):
            if t10 is None and y >= 0.1 * ss:
                t10 = t
            if t90 is None and y >= 0.9 * ss:
                t90 = t
        if t10 is not None and t90 is not None:
            return round(t90 - t10, 4)
        return float('nan')

    def peak_time(self) -> float:
        """زمان رسیدن به بیشینه"""
        max_val = max(self.output)
        idx = self.output.index(max_val)
        return round(self.time[idx], 4)

    def overshoot(self) -> float:
        """فراجهش به درصد"""
        ss = self.steady_state
        if ss == 0:
            return 0.0
        mp = max(self.output)
        os = (mp - ss) / ss * 100
        return round(max(os, 0.0), 2)

    def settling_time(self, band: float = 0.02) -> float:
        """زمان نشست (باند ±2% مقدار نهایی)"""
        ss = self.steady_state
        limit = band * abs(ss)
        settling = float('nan')
        for i in range(len(self.output) - 1, -1, -1):
            if abs(self.output[i] - ss) > limit:
                if i + 1 < len(self.time):
                    settling = round(self.time[i + 1], 4)
                break
        else:
            settling = round(self.time[0], 4)
        return settling

    def steady_state_error(self) -> float:
        """خطای حالت ماندگار"""
        final = self.output[-1] if self.output else 0
        return round(abs(self.steady_state - final), 6)

    def summary(self) -> dict:
        return {
            "زمان صعود (s)": self.rise_time(),
            "زمان اوج (s)": self.peak_time(),
            "فراجهش (%)": self.overshoot(),
            "زمان نشست (s)": self.settling_time(),
            "خطای حالت ماندگار": self.steady_state_error(),
        }


class Plotter:
    """رسم نمودار روی Canvas"""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.pad_left = 60
        self.pad_right = 20
        self.pad_top = 20
        self.pad_bottom = 50

    def draw(self, time: list, output: list, K: float,
             label: str = "", color: str = "#2196F3"):
        c = self.canvas
        W = c.winfo_width() or 600
        H = c.winfo_height() or 350

        # پاک‌سازی فقط نمودار (نه محور)
        c.delete("curve_" + label)

        if not time or not output:
            return

        x_min, x_max = 0, max(time)
        y_min = 0
        y_max = max(max(output) * 1.15, K * 1.2, 0.01)

        def tx(t):
            return (self.pad_left +
                    (t - x_min) / (x_max - x_min) *
                    (W - self.pad_left - self.pad_right))

        def ty(y):
            return (H - self.pad_bottom -
                    (y - y_min) / (y_max - y_min) *
                    (H - self.pad_top - self.pad_bottom))

        # خط مقدار نهایی
        c.create_line(tx(x_min), ty(K), tx(x_max), ty(K),
                      fill="#E91E63", dash=(6, 4), width=1,
                      tags=("curve_" + label, "curves"))
        c.create_text(W - self.pad_right - 5, ty(K) - 8,
                      text=f"SS={K:.3f}", fill="#E91E63", font=("Arial", 8),
                      anchor="e", tags=("curve_" + label, "curves"))

        # رسم منحنی
        points = []
        for t, y in zip(time, output):
            points.extend([tx(t), ty(y)])
        if len(points) >= 4:
            c.create_line(*points, fill=color, width=2, smooth=True,
                          tags=("curve_" + label, "curves"))

    def draw_axes(self, time_max: float, y_max: float):
        c = self.canvas
        c.delete("axes")
        W = c.winfo_width() or 600
        H = c.winfo_height() or 350

        pl, pr, pt, pb = self.pad_left, self.pad_right, self.pad_top, self.pad_bottom

        # محورها
        c.create_line(pl, pt, pl, H - pb, fill="#333", width=2, tags="axes")
        c.create_line(pl, H - pb, W - pr, H - pb, fill="#333", width=2, tags="axes")

        # برچسب محورها
        c.create_text(W // 2, H - 12, text="زمان (s)",
                      font=("Arial", 10), fill="#333", tags="axes")
        c.create_text(14, H // 2, text="خروجی",
                      font=("Arial", 10), fill="#333", angle=90, tags="axes")

      های محور X
        steps = 10
        for i in range(steps + 1):
            t = time_max * i / steps
            x = pl + (t / time_max) * (W - pl - pr)
            c.create_line(x, H - pb, x, H - pb + 5, fill="#333", tags="axes")
            c.create_text(x, H - pb + 15, text=f"{t:.1f}",
                          font=("Arial", 7), fill="#333", tags="axes")

       های محور Y
        for i in range(6):
            y_val = y_max * i / 5
            y = H - pb - (y_val / y_max) * (H - pt - pb)
            c.create_line(pl - 5, y, pl, y, fill="#333", tags="axes")
            c.create_text(pl - 10, y, text=f"{y_val:.2f}",
                          font=("Arial", 7), fill="#333", anchor="e", tags="axes")

        # شبکه
        for i in range(1, steps):
            x = pl + (i / steps) * (W - pl - pr)
            c.create_line(x, pt, x, H - pb, fill="#eee", tags="axes")
        for i in range(1, 6):
            y = H - pb - (i / 5) * (H - pt - pb)
            c.create_line(
