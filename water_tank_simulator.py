"""
پروژه 3: شبیه‌سازی مخزن آب و کنترل سطح
شماره دانشجویی: 03220040709006
a = 6  =>  ظرفیت مخزن = 50 * 6 = 300 لیتر
"""

import tkinter as tk
from tkinter import ttk
import math
import time
from enum import Enum
from collections import deque


# ─────────────────────────────────────────
# ثابت‌ها
# ─────────────────────────────────────────
STUDENT_ID = "03220040709006"
A = 6
TANK_CAPACITY = 50 * A          # 300 لیتر
SETPOINT_DEFAULT = TANK_CAPACITY * 0.6   # 180 لیتر (60%)
DT = 0.1                        # گام زمانی شبیه‌سازی (ثانیه)
DRAIN_RATE = 2.0                # دبی خروجی ثابت (لیتر/ثانیه)
MAX_PUMP_FLOW = 8.0             # حداکثر دبی پمپ (لیتر/ثانیه)
HISTORY_LEN = 500               # تعداد نقاط نمودار


class ControllerMode(Enum):
    MANUAL = "دستی"
    ON_OFF = "On-Off"
    PID = "PID"


# ─────────────────────────────────────────
# کلاس Tank
# ─────────────────────────────────────────
class Tank:
    """
    مدل مخزن آب.
    معادله دیفرانسیل:  dV/dt = Q_in - Q_out
    ارتفاع:            h = V / base_area
    """

    def __init__(self, capacity: float, base_area: float = 1.0):
        self.capacity = capacity          # حجم کل (لیتر)
        self.base_area = base_area        # مساحت کف (m²) — برای تبدیل حجم به ارتفاع
        self.volume = capacity * 0.3      # شروع از 30% پر
        self.overflow_count = 0
        self.dry_count = 0

    @property
    def level(self) -> float:
        """ارتفاع آب (متر)"""
        return self.volume / self.base_area

    @property
    def level_percent(self) -> float:
        """درصد پری مخزن"""
        return (self.volume / self.capacity) * 100.0

    def update(self, q_in: float, q_out: float, dt: float) -> float:
        """
        به‌روزرسانی حجم مخزن.
        q_in, q_out: دبی ورودی و خروجی (لیتر/ثانیه)
        برمی‌گرداند: حجم فعلی
        """
        delta = (q_in - q_out) * dt
        self.volume = max(0.0, min(self.capacity, self.volume + delta))

        if self.volume >= self.capacity:
            self.overflow_count += 1
        if self.volume <= 0.0:
            self.dry_count += 1

        return self.volume

    def reset(self, fill_ratio: float = 0.3):
        self.volume = self.capacity * fill_ratio
        self.overflow_count = 0
        self.dry_count = 0


# ─────────────────────────────────────────
# کلاس Pump
# ─────────────────────────────────────────
class Pump:
    """
    پمپ ورودی مخزن.
    می‌تواند روشن/خاموش یا با درصد توان کار کند.
    """

    def __init__(self, max_flow: float = MAX_PUMP_FLOW):
        self.max_flow = max_flow
        self._power = 0.0       # 0.0 تا 1.0
        self.on = False
        self.total_energy = 0.0  # مجموع انرژی مصرفی

    @property
    def flow(self) -> float:
        """دبی جاری پمپ (لیتر/ثانیه)"""
        if not self.on:
            return 0.0
        return self._power * self.max_flow

    def set_power(self, power: float):
        """تنظیم توان پمپ (0.0 تا 1.0)"""
        self._power = max(0.0, min(1.0, power))
        self.on = self._power > 0.0

    def turn_on(self):
        self.on = True
        if self._power == 0.0:
            self._power = 1.0

    def turn_off(self):
        self.on = False

    def tick(self, dt: float):
        """محاسبه انرژی مصرفی"""
        self.total_energy += self.flow * dt

    def reset(self):
        self._power = 0.0
        self.on = False
        self.total_energy = 0.0


# ─────────────────────────────────────────
# کلاس Sensor
# ─────────────────────────────────────────
class Sensor:
    """
    سنسور سطح آب.
    اضافه کردن نویز اختیاری برای واقعی‌تر شدن شبیه‌سازی.
    """

    def __init__(self, noise_std: float = 0.0):
        import random
        self._rng = random.Random(42)
        self.noise_std = noise_std
        self._last_reading = 0.0

    def read(self, true_level: float) -> float:
        """خواندن سطح آب با نویز گاوسی اختیاری"""
        noise = self._rng.gauss(0, self.noise_std) if self.noise_std > 0 else 0.0
        self._last_reading = max(0.0, true_level + noise)
        return self._last_reading

    @property
    def last(self) -> float:
        return self._last_reading


# ─────────────────────────────────────────
# کلاس Controller (On-Off و PID)
# ─────────────────────────────────────────
class Controller:
    """
    کنترلر سطح آب.
    دو حالت:
      1. On-Off: اگر سطح < setpoint → پمپ روشن، وگرنه خاموش
      2. PID:    خروجی بر اساس خطا، انتگرال و مشتق
    """

    def __init__(self, setpoint: float, mode: ControllerMode = ControllerMode.PID):
        self.setpoint = setpoint
        self.mode = mode

        # پارامترهای PID
        self.Kp = 0.5
        self.Ki = 0.05
        self.Kd = 0.1

        # حالت داخلی PID
        self._integral = 0.0
        self._prev_error = 0.0
        self._integral_limit = 50.0   # ضدسرریز انتگرال

        # آمار
        self.total_error = 0.0
        self.steps = 0

    def compute(self, measured: float, dt: float) -> float:
        """
        محاسبه خروجی کنترلر.
        برمی‌گرداند: مقدار بین 0.0 تا 1.0 (توان پمپ)
        """
        error = self.setpoint - measured
        self.total_error += abs(error)
        self.steps += 1

        if self.mode == ControllerMode.ON_OFF:
            # هیسترزیس ±5% ظرفیت برای جلوگیری از کلید‌زنی سریع
            threshold = TANK_CAPACITY * 0.05
            if measured < self.setpoint - threshold:
                return 1.0
            elif measured > self.setpoint + threshold:
                return 0.0
            else:
                # در ناحیه بی‌تفاوتی: وضعیت قبلی را حفظ کن
                return 0.5

        elif self.mode == ControllerMode.PID:
            # انتگرال‌گیر با محدودیت
            self._integral = max(
                -self._integral_limit,
                min(self._integral_limit, self._integral + error * dt)
            )
            # مشتق
            derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
            self._prev_error = error

            output = self.Kp * error + self.Ki * self._integral + self.Kd * derivative
            # نرمال‌سازی به [0, 1]
            normalized = output / TANK_CAPACITY
            return max(0.0, min(1.0, normalized))

        return 0.0

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self.total_error = 0.0
        self.steps = 0

    @property
    def mae(self) -> float:
        """میانگین قدر مطلق خطا"""
        return self.total_error / self.steps if self.steps > 0 else 0.0


# ─────────────────────────────────────────
# کلاس Simulation
# ─────────────────────────────────────────
class Simulation:
    """
    هماهنگ‌کننده اصلی شبیه‌سازی.
    هر بار step() فراخوانی شود یک گام زمانی جلو می‌رود.
    """

    def __init__(self, mode: ControllerMode = ControllerMode.PID,
                 setpoint: float = SETPOINT_DEFAULT,
                 noise_std: float = 1.0,
                 drain_rate: float = DRAIN_RATE):

        self.tank = Tank(TANK_CAPACITY)
        self.pump = Pump(MAX_PUMP_FLOW)
        self.sensor = Sensor(noise_std)
        self.controller = Controller(setpoint, mode)
        self.drain_rate = drain_rate

        self.time = 0.0
        self.mode = mode

        # تاریخچه برای نمودار
        self.history_time: deque = deque(maxlen=HISTORY_LEN)
        self.history_level: deque = deque(maxlen=HISTORY_LEN)
        self.history_setpoint: deque = deque(maxlen=HISTORY_LEN)
        self.history_pump: deque = deque(maxlen=HISTORY_LEN)

        # آمار مقایسه‌ای
        self.comparison: dict = {}

    def step(self, manual_power: float = None) -> dict:
        """
        یک گام شبیه‌سازی.
        manual_power: اگر None باشد از کنترلر استفاده می‌شود.
        """
        measured = self.sensor.read(self.tank.volume)

        if self.mode == ControllerMode.MANUAL:
            power = manual_power if manual_power is not None else 0.5
        else:
            power = self.controller.compute(measured, DT)

        self.pump.set_power(power)
        self.pump.tick(DT)

        # دبی خروجی صفر می‌شود اگر مخزن خالی باشد
        actual_drain = self.drain_rate if self.tank.volume > 0 else 0.0
        self.tank.update(self.pump.flow, actual_drain, DT)

        self.time += DT

        # ذخیره تاریخچه
        self.history_time.append(self.time)
        self.history_level.append(self.tank.level_percent)
        self.history_setpoint.append(
            (self.controller.setpoint / TANK_CAPACITY) * 100.0
        )
        self.history_pump.append(power * 100.0)

        return {
            "time": self.time,
            "volume": self.tank.volume,
            "level_pct": self.tank.level_percent,
            "pump_power": power,
            "pump_flow": self.pump.flow,
            "setpoint_pct": self.history_setpoint[-1],
            "overflow": self.tank.overflow_count,
            "dry": self.tank.dry_count,
        }

    def reset(self):
        self.tank.reset()
        self.pump.reset()
        self.controller.reset()
        self.time = 0.0
        self.history_time.clear()
        self.history_level.clear()
        self.history_setpoint.clear()
        self.history_pump.clear()

    def run_comparison(self, duration: float = 200.0) -> dict:
        """
        اجرای شبیه‌سازی برای هر سه حالت و مقایسه MAE.
        برمی‌گرداند: دیکشنری نتایج
        """
        results = {}
        for m in [ControllerMode.ON_OFF, ControllerMode.PID]:
            sim = Simulation(mode=m, setpoint=SETPOINT_DEFAULT,
                             noise_std=0.0, drain_rate=DRAIN_RATE)
            steps = int(duration / DT)
            for _ in range(steps):
                sim.step()
            results[m.value] = {
                "mae": sim.controller.mae,
                "overflow": sim.tank.overflow_count,
                "dry": sim.tank.dry_count,
                "energy": sim.pump.total_energy,
                "history_level": list(sim.history_level),
                "history_time": list(sim.history_time),
            }
        self.comparison = results
        return results


# ─────────────────────────────────────────
# کلاس GUI
# ─────────────────────────────────────────
class GUI:
    """رابط گرافیکی شبیه‌ساز مخزن آب با Tkinter"""

    # رنگ‌ها
    C_BG = "#1e1e2e"
    C_PANEL = "#2a2a3e"
    C_TEXT = "#cdd6f4"
    C_ACCENT = "#89b4fa"
    C_GREEN = "#a6e3a1"
    C_RED = "#f38ba8"
    C_YELLOW = "#f9e2af"
    C_WATER = "#74c7ec"
    C_WATER_DARK = "#1e66f5"
    C_SETPOINT = "#f38ba8"
    C_PUMP = "#a6e3a1"

    CANVAS_W = 160
    CANVAS_H = 320
    PLOT_W = 480
    PLOT_H = 180

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(
            f"شبیه‌ساز مخزن آب | ظرفیت {TANK_CAPACITY}L | دانشجو: {STUDENT_ID}"
        )
        self.root.configure(bg=self.C_BG)
        self.root.resizable(False, False)

        self.sim = Simulation()
        self.running = False
        self.manual_power = tk.DoubleVar(value=0.5)
        self._after_id = None
        self.speed = tk.IntVar(value=5)   # 1 تا 20 گام در هر فریم

        self._build_ui()
        self._draw_tank()
        self._draw_plot()

    # ── ساخت رابط ──────────────────────────
    def _build_ui(self):
        # ردیف بالا: عنوان
        title = tk.Label(
            self.root,
            text=f"🚰  شبیه‌ساز مخزن آب  |  ظرفیت = {TANK_CAPACITY} لیتر  |  a = {A}",
            bg=self.C_BG, fg=self.C_ACCENT,
            font=("Tahoma", 13, "bold")
        )
        title.grid(row=0, column=0, columnspan=3, pady=(10, 4))

        # ستون چپ: تنظیمات
        left = tk.Frame(self.root, bg=self.C_PANEL, padx=10, pady=10)
        left.grid(row=1, column=0, padx=10, pady=5, sticky="n")
        self._build_left_panel(left)

        # ستون وسط: مخزن
        mid = tk.Frame(self.root, bg=self.C_BG)
        mid.grid(row=1, column=1, padx=5, pady=5)
        self._tank_canvas = tk.Canvas(
            mid, width=self.CANVAS_W, height=self.CANVAS_H,
            bg=self.C_BG, highlightthickness=0
        )
        self._tank_canvas.pack()

        # ستون راست: اطلاعات و آمار
        right = tk.Frame(self.root, bg=self.C_PANEL, padx=10, pady=10)
        right.grid(row=1, column=2, padx=10, pady=5, sticky="n")
        self._build_right_panel(right)

        # ردیف پایین: نمودار
        plot_frame = tk.Frame(self.root, bg=self.C_BG)
        plot_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10))
        self._plot_canvas = tk.Canvas(
            plot_frame, width=self.PLOT_W, height=self.PLOT_H,
            bg=self.C_PANEL, highlightthickness=1,
            highlightbackground=self.C_ACCENT
        )
        self._plot_canvas.pack()

    def _build_left_panel(self, parent):
        tk.Label(parent, text="⚙️ تنظیمات", bg=self.C_PANEL,
                 fg=self.C_ACCENT, font=("Tahoma", 11, "bold")).pack(anchor="w")

        # حالت کنترل
        tk.Label(parent, text="حالت کنترلر:", bg=self.C_PANEL,
                 fg=self.C_TEXT, font=("Tahoma", 9)).pack(anchor="w", pady=(8, 0))
        self._mode_var = tk.StringVar(value=ControllerMode.PID.value)
        for m in ControllerMode:
            tk.Radiobutton(
                parent, text=m.value, variable=self._mode_var,
                value=m.value, bg=self.C_PANEL, fg=self.C_TEXT,
                selectcolor=self.C_BG, activebackground=self.C_PANEL,
                command=self._on_mode_change
            ).pack(anchor="w")

        tk.Label(parent, text="─" * 22, bg=self.C_PANEL, fg="#444").pack()

        # Setpoint
        tk.Label(parent, text=f"سطح هدف (0–{TANK_CAPACITY}L):",
                 bg=self.C_PANEL, fg=self.C_TEXT, font=("Tahoma", 9)).pack(anchor="w")
        self._sp_var = tk.DoubleVar(value=SETPOINT_DEFAULT)
        sp_scale = tk.Scale(
            parent, from_=0, to=TANK_CAPACITY,
            orient=tk.HORIZONTAL, variable=self._sp_var,
            bg=self.C_PANEL, fg=self.C_TEXT, troughcolor=self.C_BG,
            highlightthickness=0, length=160,
            command=lambda v: self._update_setpoint()
        )
        sp_scale.pack()

        tk.Label(parent, text="─" * 22, bg=self.C_PANEL, fg="#444").pack()

        # توان دستی
        tk.Label(parent, text="توان دستی پمپ (%):",
                 bg=self.C_PANEL, fg=self.C_TEXT, font=("Tahoma", 9)).pack(anchor="w")
        tk.Scale(
            parent, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.manual_power,
            bg=self.C_PANEL, fg=self.C_TEXT, troughcolor=self.C_BG,
            highlightthickness=0, length=160
        ).pack()

        tk.Label(parent, text="─" * 22, bg=self.C_PANEL, fg="#444").pack()

        # پارامترهای PID
        tk.Label(parent, text="پارامترهای PID:", bg=self.C_PANEL,
                 fg=self.C_YELLOW, font=("Tahoma", 9, "bold")).pack(anchor="w")
        self._kp_var = tk.DoubleVar(value=0.5)
        self._ki_var = tk.DoubleVar(value=0.05)
        self._kd_var = tk.DoubleVar(value=0.1)
        for label, var, from_, to, res in [
            ("Kp", self._kp_var, 0, 2.0, 0.01),
            ("Ki", self._ki_var, 0, 0.5, 0.005),
            ("Kd", self._kd_var, 0, 1.0, 0.01),
        ]:
            row = tk.Frame(parent, bg=self.C_PANEL)
            row.pack(fill="x")
            tk.Label(row, text=f"{label}:", bg=self.C_PANEL,
                     fg=self.C_TEXT, width=4).pack(side="left")
            tk.Scale(
                row, from_=from_, to=to, orient=tk.HORIZONTAL,
                variable=var, resolution=res,
                bg=self.C_PANEL, fg=self.C_TEXT, troughcolor=self.C_BG,
                highlightthickness=0, length=120,
                command=lambda v: self._update_pid()
            ).pack(side="left")

        tk.Label(parent, text="─" * 22, bg=self.C_PANEL, fg="#444").pack()

        # سرعت شبیه‌سازی
        tk.Label(parent, text="سرعت:", bg=self.C_PANEL,
                 fg=self.C_TEXT, font=("Tahoma", 9)).pack(anchor="w")
        tk.Scale(
            parent, from_=1, to=20, orient=tk.HORIZONTAL, variable=self.speed,
            bg=self.C_PANEL, fg=self.C_TEXT, troughcolor=self.C_BG,
            highlightthickness=0, length=160
        ).pack()

        tk.Label(parent, text="─" * 22, bg=self.C_PANEL, fg="#444").pack()

        # دکمه‌ها
        btn_cfg = dict(bg=self.C_ACCENT, fg=self.C_BG,
                       font=("Tahoma", 10, "bold"), width=14, relief="flat")
        self._btn_start = tk.Button(
            parent, text="▶  شروع", command=self._toggle, **btn_cfg)
        self._btn_start.pack(pady=3)
        tk.Button(parent, text="↺  ریست", command=self._reset, **btn_cfg).pack(pady=3)
        tk.Button(parent, text="📊  مقایسه کنترلرها",
                  command=self._show_comparison, **btn_cfg).pack(pady=3)

    def _build_right_panel(self, parent):
        tk.Label(parent, text="📊 اطلاعات لحظه‌ای", bg=self.C_PANEL,
                 fg=self.C_ACCENT, font=("Tahoma", 11, "bold")).pack(anchor="w")

        self._info_vars = {}
        fields = [
            ("زمان (s)", "time"),
            ("حجم آب (L)", "volume"),
            ("سطح (%)", "level_pct"),
            ("هدف (%)", "setpoint_pct"),
            ("توان پمپ (%)", "pump_power"),
            ("دبی پمپ (L/s)", "pump_flow"),
            ("سرریز", "overflow"),
            ("تخلیه کامل", "dry"),
        ]
        for label, key in fields:
            row = tk.Frame(parent, bg=self.C_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", bg=self.C_PANEL,
                     fg=self.C_TEXT, font=("Tahoma", 9), width=16, anchor="w").pack(side="left")
            var = tk.StringVar(value="—")
            tk.Label(row, textvariable=var, bg=self.C_PANEL,
                     fg=self.C_GREEN, font=("Tahoma", 9, "bold"), width=10).pack(side="left")
            self._info_vars[key] = var

        tk.Label(parent, text="─" * 24, bg=self.C_PANEL, fg="#444").pack()

        # نمره ویژه: نتایج مقایسه
        tk.Label(parent, text="نتایج مقایسه:", bg=self.C_PANEL,
                 fg=self.C_YELLOW, font=("Tahoma", 9, "bold")).pack(anchor="w")
        self._cmp_text = tk.Text(
            parent, width=26, height=8,
            bg=self.C_BG, fg=self.C_TEXT,
            font=("Courier", 8), relief="flat", state="disabled"
        )
        self._cmp_text.pack(pady=4)

        tk.Label(parent, text="─" * 24, bg=self.C_PANEL, fg="#444").pack()

        # نوار وضعیت
        self._status_var = tk.StringVar(value="آماده")
        tk.Label(parent, textvariable=self._status_var,
                 bg=self.C_PANEL, fg=self.C_ACCENT,
                 font=("Tahoma", 9)).pack(anchor="w")

    # ── رسم مخزن ───────────────────────────
    def _draw_tank(self):
        c = self._tank_canvas
        c.delete("all")
        W, H = self.CANVAS_W, self.CANVAS_H
        margin = 20
        tank_x0 = 30
        tank_x1 = W - 20
        tank_y0 = 30
        tank_y1 = H - 50

        level_pct = self.sim.tank.level_percent / 100.0
        sp_pct = (self.sim.controller.setpoint / TANK_CAPACITY)

        water_h = (tank_y1 - tank_y0) * level_pct
        water_y0 = tank_y1 - water_h

        # رنگ آب بر اساس سطح
        if level_pct > 0.9:
            water_color = self.C_RED
        elif level_pct < 0.1:
            water_color = "#555577"
        else:
            water_color = self.C_WATER

        # پس‌زمینه مخزن
        c.create_rectangle(tank_x0, tank_y0, tank_x1, tank_y1,
                            fill="#1a1a2e", outline=self.C_ACCENT, width=2)

        # آب
        if water_h > 0:
            c.create_rectangle(tank_x0 + 2, water_y0, tank_x1 - 2, tank_y1 - 1,
                                fill=water_color, outline="")

            # موج ساده
            wave_y = water_y0
            step = 8
            for x in range(tank_x0 + 2, tank_x1 - 2, step):
                offset = 2 * math.sin((x + self.sim.time * 5) * 0.5)
                c.create_line(x, wave_y + offset, x + step, wave_y - offset,
                              fill=self.C_WATER_DARK, width=1)

        # خط setpoint
        sp_y = tank_y1 - (tank_y1 - tank_y0) * sp_pct
        c.create_line(tank_x0, sp_y, tank_x1, sp_y,
                      fill=self.C_SETPOINT, dash=(4, 3), width=1)
        c.create_text(tank_x1 - 2, sp_y - 6,
                      text=f"SP\n{self.sim.controller.setpoint:.0f}L",
                      fill=self.C_SETPOINT, font=("Tahoma", 6),
