"""
پروژه 5: بازی تعادلی پاندول معکوس
شماره دانشجویی: 03220040709006
a = 6
"""

import tkinter as tk
from tkinter import ttk
import math
import random


class Pendulum:
    """مدل فیزیکی پاندول معکوس"""
    
    def __init__(self, length=2.0, mass=1.0, gravity=9.81):
        self.length = length  # طول پاندول (متر)
        self.mass = mass      # جرم (کیلوگرم)
        self.g = gravity      # شتاب گرانش
        
        # حالت پاندول
        self.theta = 0.0      # زاویه (رادیان) - 0 = عمودی بالا
        self.theta_dot = 0.0  # سرعت زاویه‌ای (رادیان/ثانیه)
        
        self.has_fallen = False
        self.fall_angle = math.pi / 3  # زاویه سقوط (60 درجه)
    
    def update(self, force, dt):
        """به‌روزرسانی دینامیک پاندول با نیروی اعمالی به گاری"""
        if self.has_fallen:
            return
        
        # معادله حرکت پاندول معکوس (تقریب خطی)
        # theta_ddot = (g/L)*sin(theta) + (1/L)*force*cos(theta)
        
        theta_ddot = (self.g / self.length) * math.sin(self.theta) + \
                     (force / (self.mass * self.length)) * math.cos(self.theta)
        
        # انتگرال‌گیری عددی (Euler)
        self.theta_dot += theta_ddot * dt
        self.theta += self.theta_dot * dt
        
        # چک کردن سقوط
        if abs(self.theta) > self.fall_angle:
            self.has_fallen = True
    
    def reset(self, initial_theta=0.0, initial_theta_dot=0.0):
        """ریست پاندول"""
        self.theta = initial_theta
        self.theta_dot = initial_theta_dot
        self.has_fallen = False
    
    def get_tip_position(self):
        """موقعیت نسبی نوک پاندول"""
        x = self.length * math.sin(self.theta)
        y = -self.length * math.cos(self.theta)
        return x, y


class Cart:
    """گاری که پاندول روی آن است"""
    
    def __init__(self, mass=5.0, friction=0.1):
        self.mass = mass
        self.friction = friction
        
        self.x = 0.0          # موقعیت (متر)
        self.v = 0.0          # سرعت (متر/ثانیه)
        self.max_x = 5.0      # محدوده حرکت
    
    def update(self, force, dt):
        """به‌روزرسانی موقعیت گاری"""
        # F_net = F_applied - F_friction
        net_force = force - self.friction * self.v
        
        # a = F/m
        acceleration = net_force / self.mass
        
        # انتگرال‌گیری
        self.v += acceleration * dt
        self.x += self.v * dt
        
        # محدود کردن به محدوده
        if abs(self.x) > self.max_x:
            self.x = math.copysign(self.max_x, self.x)
            self.v = 0.0
    
    def reset(self):
        """ریست گاری"""
        self.x = 0.0
        self.v = 0.0


class Sensor:
    """سنسور با قابلیت افزودن نویز"""
    
    def __init__(self, noise_std=0.0):
        self.noise_std = noise_std  # انحراف معیار نویز
    
    def read_angle(self, true_angle):
        """خواندن زاویه با نویز"""
        if self.noise_std > 0:
            noise = random.gauss(0, self.noise_std)
            return true_angle + noise
        return true_angle
    
    def read_position(self, true_position):
        """خواندن موقعیت با نویز"""
        if self.noise_std > 0:
            noise = random.gauss(0, self.noise_std * 0.1)
            return true_position + noise
        return true_position


class Controller:
    """کنترلر PD برای تعادل خودکار"""
    
    def __init__(self, kp=100.0, kd=20.0):
        self.kp = kp  # ضریب تناسبی
        self.kd = kd  # ضریب مشتقی
        self.enabled = False
    
    def compute(self, theta, theta_dot):
        """محاسبه نیروی کنترلی"""
        if not self.enabled:
            return 0.0
        
        # هدف: theta = 0, theta_dot = 0
        error = -theta
        error_dot = -theta_dot
        
        force = self.kp * error + self.kd * error_dot
        return force
    
    def toggle(self):
        """تغییر وضعیت کنترلر"""
        self.enabled = not self.enabled


class Simulation:
    """شبیه‌سازی اصلی"""
    
    def __init__(self, a=6):
        self.a = a
        self.student_id = "03220040709006"
        
        # اجزای سیستم
        self.pendulum = Pendulum(length=2.0, mass=1.0)
        self.cart = Cart(mass=5.0)
        self.sensor = Sensor(noise_std=0.0)
        self.controller = Controller(kp=100.0, kd=20.0)
        
        # پارامترهای شبیه‌سازی
        self.dt = 0.02  # 50 Hz
        self.time = 0.0
        self.manual_force = 0.0
        
        # آمار بازی
        self.score = 0
        self.balance_time = 0.0
        self.falls = 0
    
    def step(self):
        """یک گام شبیه‌سازی"""
        if self.pendulum.has_fallen:
            return
        
        # خواندن سنسورها
        measured_theta = self.sensor.read_angle(self.pendulum.theta)
        measured_x = self.sensor.read_position(self.cart.x)
        
        # محاسبه نیرو
        if self.controller.enabled:
            force = self.controller.compute(measured_theta, self.pendulum.theta_dot)
        else:
            force = self.manual_force
        
        # به‌روزرسانی سیستم
        self.cart.update(force, self.dt)
        self.pendulum.update(force, self.dt)
        
        # به‌روزرسانی آمار
        self.time += self.dt
        if not self.pendulum.has_fallen:
            self.balance_time += self.dt
            self.score = int(self.balance_time * 10)
        else:
            self.falls += 1
    
    def reset(self, add_disturbance=False):
        """ریست شبیه‌سازی"""
        initial_theta = 0.0
        initial_theta_dot = 0.0
        
        if add_disturbance:
            # شروع با اختلال کوچک
            initial_theta = random.uniform(-0.1, 0.1)
            initial_theta_dot = random.uniform(-0.2, 0.2)
        
        self.pendulum.reset(initial_theta, initial_theta_dot)
        self.cart.reset()
        self.time = 0.0
        self.manual_force = 0.0
        self.balance_time = 0.0
        self.score = 0
    
    def set_noise(self, noise_level):
        """تنظیم سطح نویز سنسور"""
        self.sensor.noise_std = noise_level


class GUI:
    """رابط گرافیکی"""
    
    def __init__(self, simulation):
        self.sim = simulation
        
        self.root = tk.Tk()
        self.root.title(f"پروژه 5: پاندول معکوس - {self.sim.student_id} - a={self.sim.a}")
        self.root.resizable(False, False)
        
        # متغیرهای GUI
        self.running = False
        self.animation_id = None
        
        self._setup_ui()
        self._setup_canvas()
        
        # کلیدهای فشرده‌شده
        self.keys_pressed = set()
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_ui(self):
        """ساخت رابط کاربری"""
        # فریم اصلی
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0)
        
        # فریم اطلاعات
        info_frame = ttk.LabelFrame(main_frame, text="اطلاعات", padding=10)
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(info_frame, text=f"شماره دانشجویی: {self.sim.student_id}").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, text=f"a = {self.sim.a}").grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        # فریم Canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.grid(row=1, column=0, columnspan=2)
        
        self.canvas = tk.Canvas(canvas_frame, width=800, height=400, bg="white")
        self.canvas.pack()
        
        # فریم کنترل
        control_frame = ttk.LabelFrame(main_frame, text="کنترل", padding=10)
        control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0), padx=(0, 5))
        
        ttk.Button(control_frame, text="▶ شروع", command=self._start).grid(row=0, column=0, padx=2)
        ttk.Button(control_frame, text="⏸ توقف", command=self._stop).grid(row=0, column=1, padx=2)
        ttk.Button(control_frame, text="🔄 ریست", command=self._reset).grid(row=0, column=2, padx=2)
        ttk.Button(control_frame, text="🎲 ریست با اختلال", command=self._reset_disturb).grid(row=0, column=3, padx=2)
        
        ttk.Label(control_frame, text="کنترل دستی: ← →").grid(row=1, column=0, columnspan=2, pady=(10, 0))
        ttk.Label(control_frame, text="نیروی دستی:").grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        self.force_scale = ttk.Scale(control_frame, from_=-50, to=50, orient="horizontal",
                                      command=self._on_force_change, length=300)
        self.force_scale.set(0)
        self.force_scale.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(5, 0))
        
        # فریم تنظیمات
        settings_frame = ttk.LabelFrame(main_frame, text="تنظیمات", padding=10)
        settings_frame.grid(row=2, column=1, sticky="ew", pady=(10, 0), padx=(5, 0))
        
        # کنترلر خودکار
        self.auto_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="کنترلر خودکار (PD)", variable=self.auto_var,
                        command=self._toggle_auto).grid(row=0, column=0, columnspan=2, sticky="w")
        
        # نویز سنسور
        ttk.Label(settings_frame, text="نویز سنسور:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.noise_scale = ttk.Scale(settings_frame, from_=0, to=0.1, orient="horizontal",
                                      command=self._on_noise_change, length=200)
        self.noise_scale.set(0)
        self.noise_scale.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        
        self.noise_label = ttk.Label(settings_frame, text="0.000")
        self.noise_label.grid(row=2, column=0, columnspan=2)
        
        # ضرایب PD
        ttk.Label(settings_frame, text="Kp:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.kp_entry = ttk.Entry(settings_frame, width=10)
        self.kp_entry.insert(0, "100")
        self.kp_entry.grid(row=3, column=1, sticky="w", pady=(10, 0))
        
        ttk.Label(settings_frame, text="Kd:").grid(row=4, column=0, sticky="w", pady=(5, 0))
        self.kd_entry = ttk.Entry(settings_frame, width=10)
        self.kd_entry.insert(0, "20")
        self.kd_entry.grid(row=4, column=1, sticky="w", pady=(5, 0))
        
        ttk.Button(settings_frame, text="اعمال", command=self._apply_pd).grid(row=5, column=0, columnspan=2, pady=(5, 0))
        
        # فریم وضعیت
        status_frame = ttk.LabelFrame(main_frame, text="وضعیت", padding=10)
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="", font=("Arial", 10))
        self.status_label.pack()
    
    def _setup_canvas(self):
        """تنظیمات اولیه Canvas"""
        self._draw()
    
    def _draw(self):
        """رسم صحنه"""
        self.canvas.delete("all")
        
        # مختصات مرکز
        cx = 400
        cy = 300
        scale = 60  # پیکسل به متر
        
        # محدوده حرکت
        max_x_pixel = self.sim.cart.max_x * scale
        self.canvas.create_line(cx - max_x_pixel, cy, cx + max_x_pixel, cy,
                                fill="gray", width=2)
        
        # موقعیت گاری
        cart_x = cx + self.sim.cart.x * scale
        
        # رسم گاری
        cart_width = 60
        cart_height = 30
        cart_color = "blue" if not self.sim.pendulum.has_fallen else "gray"
        self.canvas.create_rectangle(cart_x - cart_width/2, cy - cart_height/2,
                                      cart_x + cart_width/2, cy + cart_height/2,
                                      fill=cart_color, outline="black", width=2)
        
        # رسم پاندول
        tip_x, tip_y = self.sim.pendulum.get_tip_position()
        tip_x_pixel = cart_x + tip_x * scale
        tip_y_pixel = cy - tip_y * scale
        
        pendulum_color = "red" if self.sim.pendulum.has_fallen else "darkgreen"
        
        # میله پاندول
        self.canvas.create_line(cart_x, cy, tip_x_pixel, tip_y_pixel,
                                fill=pendulum_color, width=4)
        
        # توپ انتهای پاندول
        ball_radius = 10
        self.canvas.create_oval(tip_x_pixel - ball_radius, tip_y_pixel - ball_radius,
                                tip_x_pixel + ball_radius, tip_y_pixel + ball_radius,
                                fill=pendulum_color, outline="black", width=2)
        
        # محدوده سقوط
        fall_angle = self.sim.pendulum.fall_angle
        fall_x_left = -self.sim.pendulum.length * math.sin(fall_angle) * scale
        fall_x_right = self.sim.pendulum.length * math.sin(fall_angle) * scale
        fall_y = -self.sim.pendulum.length * math.cos(fall_angle) * scale
        
        self.canvas.create_line(cart_x + fall_x_left, cy + fall_y,
                                cart_x + fall_x_left, cy,
                                fill="orange", dash=(5, 5), width=2)
        self.canvas.create_line(cart_x + fall_x_right, cy + fall_y,
                                cart_x + fall_x_right, cy,
                                fill="orange", dash=(5, 5), width=2)
        
        # اطلاعات
        info_text = f"زمان: {self.sim.time:.1f}s | زاویه: {math.degrees(self.sim.pendulum.theta):.1f}° | امتیاز: {self.sim.score}"
        if self.sim.pendulum.has_fallen:
            info_text += " | ❌ سقوط کرد!"
        
        self.canvas.create_text(400, 20, text=info_text, font=("Arial", 12, "bold"))
        
        # راهنما
        help_text = "← → : حرکت گاری | Space : ریست | A : کنترلر خودکار"
        self.canvas.create_text(400, 380, text=help_text, font=("Arial", 10), fill="gray")
        
        # وضعیت
        status = f"زمان تعادل: {self.sim.balance_time:.1f}s | تعداد سقوط: {self.sim.falls}"
        if self.sim.controller.enabled:
            status += " | کنترلر: فعال"
        if self.sim.sensor.noise_std > 0:
            status += f" | نویز: {self.sim.sensor.noise_std:.3f}"
        
        self.status_label.config(text=status)
    
    def _start(self):
        """شروع شبیه‌سازی"""
        if not self.running:
            self.running = True
            self._animate()
    
    def _stop(self):
        """توقف شبیه‌سازی"""
        self.running = False
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
    
    def _reset(self):
        """ریست بدون اختلال"""
        self._stop()
        self.sim.reset(add_disturbance=False)
        self._draw()
    
    def _reset_disturb(self):
        """ریست با اختلال"""
        self._stop()
        self.sim.reset(add_disturbance=True)
        self._draw()
    
    def _animate(self):
        """حلقه انیمیشن"""
        if not self.running:
            return
        
        # اعمال نیروی دستی از کلیدها
        if not self.sim.controller.enabled:
            if "Left" in self.keys_pressed:
                self.sim.manual_force = -30
            elif "Right" in self.keys_pressed:
                self.sim.manual_force = 30
            else:
                self.sim.manual_force = 0
        
        # یک گام شبیه‌سازی
        self.sim.step()
        
        # رسم
        self._draw()
        
        # بررسی سقوط
        if self.sim.pendulum.has_fallen:
            self._stop()
            return
        
        # بعدی
        self.animation_id = self.root.after(int(self.sim.dt * 1000), self._animate)
    
    def _toggle_auto(self):
        """فعال/غیرفعال کردن کنترلر"""
        self.sim.controller.enabled = self.auto_var.get()
        if self.sim.controller.enabled:
            self.force_scale.config(state="disabled")
        else:
            self.force_scale.config(state="normal")
    
    def _on_force_change(self, value):
        """تغییر نیروی دستی"""
        if not self.sim.controller.enabled:
            self.sim.manual_force = float(value)
    
    def _on_noise_change(self, value):
        """تغییر سطح نویز"""
        noise = float(value)
        self.sim.set_noise(noise)
        self.noise_label.config(text=f"{noise:.3f}")
    
    def _apply_pd(self):
        """اعمال ضرایب PD"""
        try:
            kp = float(self.kp_entry.get())
            kd = float(self.kd_entry.get())
            self.sim.controller.kp = kp
            self.sim.controller.kd = kd
        except ValueError:
            pass
    
    def _on_key_press(self, event):
        """فشردن کلید"""
        self.keys_pressed.add(event.keysym)
        
        if event.keysym == "space":
            self._reset()
        elif event.keysym == "a" or event.keysym == "A":
            self.auto_var.set(not self.auto_var.get())
            self._toggle_auto()
    
    def _on_key_release(self, event):
        """رها کردن کلید"""
        self.keys_pressed.discard(event.keysym)
    
    def _on_close(self):
        """بستن پنجره"""
        self._stop()
        self.root.destroy()
    
    def run(self):
        """اجرای GUI"""
        self.root.mainloop()


def main():
    """تابع اصلی"""
    # مشخصات
    a = 6
    student_id = "03220040709006"
    
    print(f"پروژه 5: بازی تعادلی پاندول معکوس")
    print(f"شماره دانشجویی: {student_id}")
    print(f"a = {a}")
    print("-" * 50)
    
    # ساخت شبیه‌سازی
    sim = Simulation(a=a)
    
    # اجرای GUI
    gui = GUI(sim)
    gui.run()


if __name__ == "__main__":
    main()
