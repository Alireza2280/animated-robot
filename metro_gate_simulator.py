"""
پروژه 6: شبیه‌ساز گیت مترو
سیستم کارت، سنسور و موتور باز/بسته شدن

شماره دانشجویی: 03220040709006
a = 6
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from enum import Enum
import random


# ================== Card ==================
class CardType(Enum):
    SINGLE = "یک‌بار مصرف"
    DAILY = "روزانه"
    MONTHLY = "ماهانه"


class Card:
    """کارت مترو"""
    
    def __init__(self, card_id, balance=0, card_type=CardType.SINGLE):
        self.id = card_id
        self.balance = balance
        self.type = card_type
        self.is_valid = True
        self.last_entry = None
        self.trips = 0
        self.blocked = False
    
    def charge(self, amount):
        """شارژ کارت"""
        if amount > 0:
            self.balance += amount
            return True
        return False
    
    def can_enter(self, fare=10000):
        """بررسی امکان ورود"""
        if self.blocked or not self.is_valid:
            return False, "کارت مسدود یا نامعتبر است"
        
        if self.type == CardType.MONTHLY:
            return True, "کارت ماهانه معتبر"
        elif self.type == CardType.DAILY:
            # بررسی تاریخ
            if self.last_entry and self.last_entry.date() == datetime.now().date():
                return True, "کارت روزانه معتبر"
            elif self.balance >= fare:
                return True, "اولین استفاده امروز"
            else:
                return False, "موجودی کافی نیست"
        else:  # SINGLE
            if self.balance >= fare:
                return True, "موجودی کافی"
            else:
                return False, f"موجودی کارت: {self.balance:,} ریال"
    
    def deduct(self, amount):
        """کسر مبلغ از کارت"""
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False
    
    def enter_station(self, fare=10000):
        """ثبت ورود به ایستگاه"""
        can, msg = self.can_enter(fare)
        if not can:
            return False, msg
        
        if self.type == CardType.SINGLE or (self.type == CardType.DAILY and 
            (not self.last_entry or self.last_entry.date() != datetime.now().date())):
            if not self.deduct(fare):
                return False, "خطا در کسر مبلغ"
        
        self.last_entry = datetime.now()
        self.trips += 1
        return True, "ورود موفق"
    
    def exit_station(self):
        """خروج از ایستگاه"""
        pass


# ================== Passenger ==================
class Passenger:
    """مسافر"""
    
    def __init__(self, passenger_id, name, card=None):
        self.id = passenger_id
        self.name = name
        self.card = card
        self.position = "بیرون"  # بیرون / نزدیک گیت / داخل
    
    def has_valid_card(self):
        """بررسی داشتن کارت معتبر"""
        return self.card is not None and self.card.is_valid and not self.card.blocked
    
    def approach_gate(self):
        """نزدیک شدن به گیت"""
        self.position = "نزدیک گیت"
    
    def pass_gate(self):
        """عبور از گیت"""
        self.position = "داخل"
    
    def reset_position(self):
        """بازگشت به موقعیت اولیه"""
        self.position = "بیرون"


# ================== Sensor ==================
class SensorType(Enum):
    CARD_READER = "کارت‌خوان"
    APPROACH = "تشخیص نزدیک شدن"
    PASS_THROUGH = "تشخیص عبور"
    ANTI_PASSBACK = "ضد برگشت"


class Sensor:
    """سنسور"""
    
    def __init__(self, sensor_type):
        self.type = sensor_type
        self.is_active = False
        self.last_detection_time = None
        self.detection_count = 0
    
    def detect(self, obj=None):
        """تشخیص شی"""
        self.is_active = True
        self.last_detection_time = datetime.now()
        self.detection_count += 1
        return True
    
    def clear(self):
        """پاک کردن وضعیت سنسور"""
        self.is_active = False
    
    def time_since_detection(self):
        """زمان از آخرین تشخیص"""
        if self.last_detection_time:
            return (datetime.now() - self.last_detection_time).total_seconds()
        return None
    
    def reset(self):
        """ریست سنسور"""
        self.is_active = False
        self.last_detection_time = None


# ================== Motor ==================
class Motor:
    """موتور گیت"""
    
    def __init__(self, open_angle=90, speed=2.0):
        self.position = 0  # 0 = بسته، open_angle = باز
        self.target = 0
        self.open_angle = open_angle
        self.speed = speed  # درجه بر فریم
        self.is_moving = False
        self.total_cycles = 0
    
    def open(self):
        """باز کردن گیت"""
        self.target = self.open_angle
        self.is_moving = True
    
    def close(self):
        """بستن گیت"""
        self.target = 0
        self.is_moving = True
    
    def update(self):
        """به‌روزرسانی موقعیت موتور"""
        if not self.is_moving:
            return
        
        if abs(self.position - self.target) < self.speed:
            self.position = self.target
            self.is_moving = False
            if self.target == 0:
                self.total_cycles += 1
        else:
            if self.position < self.target:
                self.position += self.speed
            else:
                self.position -= self.speed
    
    def is_open(self):
        """بررسی باز بودن"""
        return abs(self.position - self.open_angle) < 1
    
    def is_closed(self):
        """بررسی بسته بودن"""
        return abs(self.position) < 1
    
    def reset(self):
        """ریست موتور"""
        self.position = 0
        self.target = 0
        self.is_moving = False


# ================== Gate ==================
class GateState(Enum):
    IDLE = "آماده"
    WAITING_CARD = "در انتظار کارت"
    CARD_ACCEPTED = "کارت پذیرفته شد"
    CARD_REJECTED = "کارت رد شد"
    OPENING = "در حال باز شدن"
    OPEN = "باز"
    WAITING_PASS = "در انتظار عبور"
    CLOSING = "در حال بسته شدن"
    ALARM = "هشدار"


class Gate:
    """گیت مترو"""
    
    def __init__(self, gate_id, fare=10000):
        self.id = gate_id
        self.fare = fare
        self.state = GateState.IDLE
        
        # سنسورها
        self.card_reader = Sensor(SensorType.CARD_READER)
        self.approach_sensor = Sensor(SensorType.APPROACH)
        self.pass_sensor = Sensor(SensorType.PASS_THROUGH)
        self.anti_passback = Sensor(SensorType.ANTI_PASSBACK)
        
        # موتور
        self.motor = Motor(open_angle=90, speed=3.0)
        
        # آمار
        self.total_entries = 0
        self.total_rejections = 0
        self.total_revenue = 0
        self.violations = 0
        
        self.current_card = None
        self.message = "گیت آماده است"
        self.alarm_active = False
    
    def scan_card(self, card):
        """اسکن کارت"""
        self.card_reader.detect(card)
        self.current_card = card
        
        can_enter, msg = card.can_enter(self.fare)
        
        if can_enter:
            success, entry_msg = card.enter_station(self.fare)
            if success:
                self.state = GateState.CARD_ACCEPTED
                self.message = f"✓ {entry_msg}\nموجودی: {card.balance:,} ریال"
                self.motor.open()
                self.total_entries += 1
                self.total_revenue += self.fare if card.type == CardType.SINGLE else 0
                return True
            else:
                self.state = GateState.CARD_REJECTED
                self.message = f"✗ {entry_msg}"
                self.total_rejections += 1
                return False
        else:
            self.state = GateState.CARD_REJECTED
            self.message = f"✗ {msg}"
            self.total_rejections += 1
            return False
    
    def detect_approach(self):
        """تشخیص نزدیک شدن مسافر"""
        self.approach_sensor.detect()
        if self.state == GateState.IDLE:
            self.state = GateState.WAITING_CARD
            self.message = "لطفاً کارت خود را اسکن کنید"
    
    def detect_pass(self):
        """تشخیص عبور مسافر"""
        self.pass_sensor.detect()
        if self.motor.is_open():
            self.state = GateState.WAITING_PASS
            self.message = "مسافر در حال عبور..."
    
    def complete_pass(self):
        """تکمیل عبور"""
        if self.pass_sensor.is_active:
            self.motor.close()
            self.state = GateState.CLOSING
            self.message = "عبور موفق - گیت در حال بسته شدن"
            self.pass_sensor.clear()
    
    def detect_violation(self):
        """تشخیص تخلف"""
        self.anti_passback.detect()
        self.alarm_active = True
        self.state = GateState.ALARM
        self.message = "⚠ هشدار: تخلف شناسایی شد!"
        self.violations += 1
        self.motor.close()
    
    def reset_alarm(self):
        """ریست آلارم"""
        self.alarm_active = False
        self.anti_passback.clear()
        if self.motor.is_closed():
            self.state = GateState.IDLE
            self.message = "گیت آماده است"
    
    def update(self):
        """به‌روزرسانی وضعیت گیت"""
        self.motor.update()
        
        # بستن خودکار بعد از عبور
        if self.state == GateState.WAITING_PASS and self.pass_sensor.time_since_detection():
            if self.pass_sensor.time_since_detection() > 2.0:
                self.complete_pass()
        
        # بازگشت به حالت IDLE
        if self.state == GateState.CLOSING and self.motor.is_closed():
            self.state = GateState.IDLE
            self.message = "گیت آماده است"
            self.current_card = None
            self.approach_sensor.clear()
            self.card_reader.clear()
        
        # بازگشت از OPENING به OPEN
        if self.state == GateState.OPENING and self.motor.is_open():
            self.state = GateState.OPEN
    
    def force_close(self):
        """بستن اجباری"""
        self.motor.close()
        self.state = GateState.CLOSING
        self.message = "بستن اجباری گیت"
    
    def reset(self):
        """ریست کامل گیت"""
        self.motor.reset()
        self.state = GateState.IDLE
        self.message = "گیت آماده است"
        self.alarm_active = False
        self.current_card = None
        self.approach_sensor.reset()
        self.card_reader.reset()
        self.pass_sensor.reset()
        self.anti_passback.reset()


# ================== GUI ==================
class MetroGateGUI:
    """رابط گرافیکی شبیه‌ساز گیت مترو"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"شبیه‌ساز گیت مترو - پروژه 6 - شماره دانشجویی: 03220040709006 (a=6)")
        self.root.geometry("1100x750")
        self.root.resizable(False, False)
        
        # متغیرها
        self.gate = Gate(gate_id="G-006", fare=10000 * 6)  # کرایه = a × 10000
        self.passengers = self._create_sample_passengers()
        self.selected_passenger = None
        self.animation_running = False
        
        self._setup_ui()
        self._update_display()
    
    def _create_sample_passengers(self):
        """ایجاد مسافران نمونه"""
        passengers = [
            Passenger("P001", "علی احمدی", Card("C001", 100000, CardType.SINGLE)),
            Passenger("P002", "مریم کریمی", Card("C002", 200000, CardType.DAILY)),
            Passenger("P003", "رضا محمدی", Card("C003", 0, CardType.MONTHLY)),
            Passenger("P004", "فاطمه رضایی", Card("C004", 30000, CardType.SINGLE)),
            Passenger("P005", "حسین نوری", Card("C005", 0, CardType.SINGLE)),
        ]
        return passengers
    
    def _setup_ui(self):
        """ساخت رابط کاربری"""
        # فریم اصلی
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # فریم بالا - اطلاعات پروژه
        info_frame = tk.LabelFrame(main_frame, text="اطلاعات پروژه", font=("Arial", 10, "bold"),
                                    bg="#e8f4f8", padx=10, pady=5)
        info_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        tk.Label(info_frame, text="پروژه 6: شبیه‌ساز گیت مترو | شماره دانشجویی: 03220040709006 | a = 6 | کرایه: 60,000 ریال",
                 font=("Arial", 10), bg="#e8f4f8").pack()
        
        # ستون چپ - انتخاب مسافر و کنترل‌ها
        left_frame = tk.LabelFrame(main_frame, text="کنترل", font=("Arial", 10, "bold"),
                                    bg="white", padx=10, pady=10)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        # انتخاب مسافر
        tk.Label(left_frame, text="انتخاب مسافر:", font=("Arial", 9, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        
        self.passenger_listbox = tk.Listbox(left_frame, height=6, font=("Arial", 9))
        self.passenger_listbox.pack(fill=tk.BOTH, pady=(0, 10))
        for p in self.passengers:
            card_info = f"{p.card.type.value} ({p.card.balance:,})" if p.card else "بدون کارت"
            self.passenger_listbox.insert(tk.END, f"{p.name} - {card_info}")
        
        # دکمه‌ها
        btn_frame = tk.Frame(left_frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="🚶 نزدیک شدن به گیت", command=self._approach_gate,
                  bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="💳 اسکن کارت", command=self._scan_card,
                  bg="#2196F3", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="➡ عبور از گیت", command=self._pass_gate,
                  bg="#FF9800", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="🔄 عبور خودکار", command=self._auto_pass,
                  bg="#9C27B0", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        
        tk.Label(left_frame, text="", bg="white").pack(pady=5)
        
        tk.Button(left_frame, text="⚠ شبیه‌سازی تخلف", command=self._simulate_violation,
                  bg="#f44336", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="🔓 ریست آلارم", command=self._reset_alarm,
                  bg="#795548", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="❌ بستن اجباری", command=self._force_close,
                  bg="#607D8B", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        
        tk.Label(left_frame, text="", bg="white").pack(pady=5)
        
        tk.Button(left_frame, text="💰 شارژ کارت", command=self._charge_card,
                  bg="#009688", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="🔄 ریست گیت", command=self._reset_gate,
                  bg="#555555", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=2)
        
        # ستون وسط - نمایش گیت
        center_frame = tk.LabelFrame(main_frame, text="نمایش گیت", font=("Arial", 10, "bold"),
                                      bg="white", padx=10, pady=10)
        center_frame.grid(row=1, column=1, sticky="nsew", padx=5)
        
        self.canvas = tk.Canvas(center_frame, width=400, height=500, bg="#f5f5f5", highlightthickness=1)
        self.canvas.pack()
        
        # ستون راست - وضعیت و آمار
        right_frame = tk.LabelFrame(main_frame, text="وضعیت و آمار", font=("Arial", 10, "bold"),
                                     bg="white", padx=10, pady=10)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(5, 0))
        
        # وضعیت گیت
        status_frame = tk.LabelFrame(right_frame, text="وضعیت", bg="white", font=("Arial", 9, "bold"))
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.state_label = tk.Label(status_frame, text="", font=("Arial", 10, "bold"),
                                     bg="white", fg="#2196F3", wraplength=250, justify="right")
        self.state_label.pack(pady=5)
        
        self.message_label = tk.Label(status_frame, text="", font=("Arial", 9),
                                       bg="white", wraplength=250, justify="right")
        self.message_label.pack(pady=5)
        
        # سنسورها
        sensor_frame = tk.LabelFrame(right_frame, text="سنسورها", bg="white", font=("Arial", 9, "bold"))
        sensor_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.sensor_labels = {}
        sensors = [
            ("approach", "نزدیک شدن"),
            ("card", "کارت‌خوان"),
            ("pass", "عبور"),
            ("anti", "ضد برگشت")
        ]
        
        for key, name in sensors:
            frame = tk.Frame(sensor_frame, bg="white")
            frame.pack(fill=tk.X, pady=2)
            tk.Label(frame, text=f"{name}:", font=("Arial", 8), bg="white", width=12, anchor="e").pack(side=tk.RIGHT)
            lbl = tk.Label(frame, text="●", font=("Arial", 12), bg="white", fg="gray")
            lbl.pack(side=tk.RIGHT, padx=5)
            self.sensor_labels[key] = lbl
        
        # موتور
        motor_frame = tk.LabelFrame(right_frame, text="موتور", bg="white", font=("Arial", 9, "bold"))
        motor_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.motor_position_label = tk.Label(motor_frame, text="", font=("Arial", 9), bg="white")
        self.motor_position_label.pack(pady=5)
        
        self.motor_status_label = tk.Label(motor_frame, text="", font=("Arial", 8), bg="white", fg="#666")
        self.motor_status_label.pack()
        
        # آمار
        stats_frame = tk.LabelFrame(right_frame, text="آمار", bg="white", font=("Arial", 9, "bold"))
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        self.stats_text = tk.Text(stats_frame, height=10, font=("Arial", 9), bg="white",
                                   relief=tk.FLAT, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # تنظیم وزن ستون‌ها
        main_frame.columnconfigure(0, weight=1, minsize=250)
        main_frame.columnconfigure(1, weight=2, minsize=400)
        main_frame.columnconfigure(2, weight=1, minsize=280)
        main_frame.rowconfigure(1, weight=1)
    
    def _draw_gate(self):
        """رسم گیت"""
        self.canvas.delete("all")
        
        # زمینه
        self.canvas.create_rectangle(0, 0, 400, 500, fill="#f5f5f5", outline="")
        
        # خط زمین
        self.canvas.create_line(0, 400, 400, 400, fill="#333", width=2)
        
        # بدنه گیت
        # پایه چپ
        self.canvas.create_rectangle(50, 250, 90, 400, fill="#455A64", outline="#263238", width=2)
        # پایه راست
        self.canvas.create_rectangle(310, 250, 350, 400, fill="#455A64", outline="#263238", width=2)
        
        # کارت‌خوان
        self.canvas.create_rectangle(60, 280, 80, 310, fill="#2196F3", outline="#1976D2", width=2)
        self.canvas.create_text(70, 295, text="💳", font=("Arial", 16))
        
        # LED نمایشگر
        color = "#4CAF50" if self.gate.state == GateState.CARD_ACCEPTED else \
                "#f44336" if self.gate.state == GateState.CARD_REJECTED or self.gate.alarm_active else "#FFC107"
        self.canvas.create_oval(320, 270, 340, 290, fill=color, outline="#333", width=2)
        
        # درب گیت (چرخشی)
        angle = self.gate.motor.position
        
        # محاسبه موقعیت درب
        center_x, center_y = 200, 325
        arm_length = 100
        
        # بازوی درب
        import math
        rad = math.radians(angle)
        end_x = center_x + arm_length * math.cos(rad)
        end_y = center_y - arm_length * math.sin(rad)
        
        # محور مرکزی
        self.canvas.create_oval(195, 320, 205, 330, fill="#333", outline="#000", width=2)
        
        # بازوی درب
        self.canvas.create_line(center_x, center_y, end_x, end_y, fill="#FF5722", width=8)
        self.canvas.create_oval(end_x-8, end_y-8, end_x+8, end_y+8, fill="#D84315", outline="#BF360C", width=2)
        
        # زاویه
        self.canvas.create_text(200, 360, text=f"{angle:.0f}°", font=("Arial", 12, "bold"))
        
        # سنسورها
        approach_color = "#4CAF50" if self.gate.approach_sensor.is_active else "#BDBDBD"
        self.canvas.create_rectangle(30, 370, 50, 385, fill=approach_color, outline="#333", width=2)
        self.canvas.create_text(40, 390, text="نزدیک", font=("Arial", 7))
        
        pass_color = "#4CAF50" if self.gate.pass_sensor.is_active else "#BDBDBD"
        self.canvas.create_rectangle(190, 370, 210, 385, fill=pass_color, outline="#333", width=2)
        self.canvas.create_text(200, 390, text="عبور", font=("Arial", 7))
        
        anti_color = "#f44336" if self.gate.anti_passback.is_active else "#BDBDBD"
        self.canvas.create_rectangle(350, 370, 370, 385, fill=anti_color, outline="#333", width=2)
        self.canvas.create_text(360, 390, text="ضد", font=("Arial", 7))
        
        # مسافر
        if self.selected_passenger:
            pos = self.selected_passenger.position
            if pos == "بیرون":
                x, y = 30, 340
            elif pos == "نزدیک گیت":
                x, y = 100, 340
            elif pos == "داخل":
                x, y = 300, 340
            else:
                x, y = -100, -100
            
            if x > 0:
                # سر
                self.canvas.create_oval(x-15, y-40, x+15, y-10, fill="#FFD700", outline="#333", width=2)
                # بدن
                self.canvas.create_line(x, y-10, x, y+20, fill="#333", width=6)
                # دست‌ها
                self.canvas.create_line(x, y, x-15, y+10, fill="#333", width=4)
                self.canvas.create_line(x, y, x+15, y+10, fill="#333", width=4)
                # پاها
                self.canvas.create_line(x, y+20, x-10, y+45, fill="#333", width=5)
                self.canvas.create_line(x, y+20, x+10, y+45, fill="#333", width=5)
                # نام
                self.canvas.create_text(x, y+55, text=self.selected_passenger.name, font=("Arial", 8, "bold"))
        
        # آلارم
        if self.gate.alarm_active:
            self.canvas.create_text(200, 50, text="⚠ ALARM ⚠", font=("Arial", 24, "bold"),
                                    fill="#f44336")
            self.canvas.create_rectangle(10, 30, 390, 80, outline="#f44336", width=4)
        
        # وضعیت
        state_text = self.gate.state.value
        self.canvas.create_text(200, 450, text=state_text, font=("Arial", 14, "bold"), fill="#1976D2")
    
    def _update_display(self):
        """به‌روزرسانی نمایش"""
        self._draw_gate()
        
        # وضعیت
        self.state_label.config(text=self.gate.state.value)
        self.message_label.config(text=self.gate.message)
        
        # سنسورها
