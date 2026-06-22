import tkinter as tk
from tkinter import ttk
import time
from collections import deque
from enum import Enum

class Direction(Enum):
    IDLE = 0
    UP = 1
    DOWN = -1

class Person:
    """کلاس نمایش یک مسافر"""
    def __init__(self, person_id, current_floor, destination_floor):
        self.id = person_id
        self.current_floor = current_floor
        self.destination_floor = destination_floor
        self.wait_time = 0
        self.in_elevator = False
    
    def get_direction(self):
        """جهت حرکت مورد نیاز مسافر"""
        if self.destination_floor > self.current_floor:
            return Direction.UP
        elif self.destination_floor < self.current_floor:
            return Direction.DOWN
        return Direction.IDLE

class Floor:
    """کلاس نمایش یک طبقه"""
    def __init__(self, floor_number):
        self.number = floor_number
        self.waiting_people = []
    
    def add_person(self, person):
        """افزودن مسافر به صف انتظار طبقه"""
        self.waiting_people.append(person)
    
    def remove_person(self, person):
        """حذف مسافر از صف انتظار"""
        if person in self.waiting_people:
            self.waiting_people.remove(person)

class Elevator:
    """کلاس آسانسور"""
    def __init__(self, capacity=8):
        self.current_floor = 0
        self.direction = Direction.IDLE
        self.passengers = []
        self.capacity = capacity
        self.total_distance = 0
    
    def can_board(self):
        """آیا ظرفیت برای سوار شدن مسافر جدید هست؟"""
        return len(self.passengers) < self.capacity
    
    def board_passenger(self, person):
        """سوار کردن مسافر"""
        if self.can_board():
            self.passengers.append(person)
            person.in_elevator = True
            return True
        return False
    
    def unboard_passengers(self, floor_number):
        """پیاده کردن مسافران در طبقه مقصد"""
        unboarded = []
        for person in self.passengers[:]:
            if person.destination_floor == floor_number:
                self.passengers.remove(person)
                unboarded.append(person)
        return unboarded
    
    def move(self, target_floor):
        """حرکت آسانسور به طبقه هدف"""
        if target_floor > self.current_floor:
            self.direction = Direction.UP
            self.current_floor += 1
        elif target_floor < self.current_floor:
            self.direction = Direction.DOWN
            self.current_floor -= 1
        else:
            self.direction = Direction.IDLE
        
        self.total_distance += 1

class Controller:
    """کنترلر آسانسور - مدیریت درخواست‌ها"""
    def __init__(self, building):
        self.building = building
        self.requests = deque()  # صف درخواست‌ها
        self.destinations = set()  # طبقات مقصد
    
    def add_request(self, floor_number):
        """افزودن درخواست طبقه"""
        if floor_number not in self.destinations:
            self.requests.append(floor_number)
            self.destinations.add(floor_number)
    
    def get_next_floor(self):
        """تعیین طبقه بعدی بر اساس الگوریتم SCAN"""
        elevator = self.building.elevator
        current = elevator.current_floor
        direction = elevator.direction
        
        # جمع‌آوری تمام درخواست‌ها
        all_targets = set(self.requests)
        
        # افزودن مقاصد مسافران داخل آسانسور
        for person in elevator.passengers:
            all_targets.add(person.destination_floor)
        
        # افزودن طبقاتی که مسافر منتظر دارند
        for floor in self.building.floors:
            if floor.waiting_people:
                all_targets.add(floor.number)
        
        if not all_targets:
            return None
        
        # الگوریتم SCAN (رفت و برگشت)
        if direction == Direction.UP or direction == Direction.IDLE:
            # اولویت به طبقات بالاتر
            higher = [f for f in all_targets if f >= current]
            if higher:
                return min(higher)
            else:
                # تغییر جهت به پایین
                return max(all_targets)
        else:  # DOWN
            # اولویت به طبقات پایین‌تر
            lower = [f for f in all_targets if f <= current]
            if lower:
                return max(lower)
            else:
                # تغییر جهت به بالا
                return min(all_targets)
    
    def remove_request(self, floor_number):
        """حذف درخواست پس از رسیدن"""
        if floor_number in self.destinations:
            self.destinations.remove(floor_number)
        if floor_number in self.requests:
            self.requests.remove(floor_number)

class Building:
    """کلاس ساختمان - مدیریت کل سیستم"""
    def __init__(self, num_floors):
        self.num_floors = num_floors
        self.floors = [Floor(i) for i in range(num_floors)]
        self.elevator = Elevator()
        self.controller = Controller(self)
        self.time = 0
        self.person_counter = 0
    
    def add_person_request(self, current_floor, destination_floor):
        """افزودن مسافر جدید"""
        if 0 <= current_floor < self.num_floors and 0 <= destination_floor < self.num_floors:
            person = Person(self.person_counter, current_floor, destination_floor)
            self.person_counter += 1
            self.floors[current_floor].add_person(person)
            self.controller.add_request(current_floor)
            return person
        return None
    
    def step(self):
        """یک گام شبیه‌سازی"""
        self.time += 1
        
        # افزایش زمان انتظار مسافران
        for floor in self.floors:
            for person in floor.waiting_people:
                person.wait_time += 1
        
        # تعیین طبقه هدف بعدی
        next_floor = self.controller.get_next_floor()
        
        if next_floor is not None:
            # حرکت آسانسور
            if self.elevator.current_floor != next_floor:
                self.elevator.move(next_floor)
            else:
                # رسیدن به طبقه هدف
                current_floor_num = self.elevator.current_floor
                
                # پیاده کردن مسافران
                unboarded = self.elevator.unboard_passengers(current_floor_num)
                
                # سوار کردن مسافران منتظر با همان جهت
                floor = self.floors[current_floor_num]
                for person in floor.waiting_people[:]:
                    if self.elevator.can_board():
                        person_direction = person.get_direction()
                        # فقط مسافرانی که همجهت با آسانسور هستند
                        if (self.elevator.direction == Direction.IDLE or 
                            person_direction == self.elevator.direction or
                            len(self.elevator.passengers) == 0):
                            if self.elevator.board_passenger(person):
                                floor.remove_person(person)
                
                # حذف این طبقه از درخواست‌ها
                self.controller.remove_request(current_floor_num)
        else:
            # آسانسور بیکار است
            self.elevator.direction = Direction.IDLE

class GUI:
    """رابط گرافیکی"""
    def __init__(self, building):
        self.building = building
        self.root = tk.Tk()
        self.root.title(f"شبیه‌ساز آسانسور هوشمند - ساختمان {building.num_floors} طبقه")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        self.running = False
        self.speed = 500  # میلی‌ثانیه
        
        self.setup_ui()
    
    def setup_ui(self):
        """طراحی رابط کاربری"""
        # فریم کنترل
        control_frame = tk.Frame(self.root, bg='#e0e0e0', padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(control_frame, text="طبقه فعلی:", bg='#e0e0e0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.current_floor_entry = tk.Entry(control_frame, width=5)
        self.current_floor_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="طبقه مقصد:", bg='#e0e0e0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.dest_floor_entry = tk.Entry(control_frame, width=5)
        self.dest_floor_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="افزودن مسافر", command=self.add_person_ui, 
                 bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.start_button = tk.Button(control_frame, text="شروع", command=self.toggle_simulation,
                                      bg='#2196F3', fg='white', font=('Arial', 10))
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="سرعت:", bg='#e0e0e0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.speed_scale = tk.Scale(control_frame, from_=100, to=1000, orient=tk.HORIZONTAL,
                                    command=self.change_speed, length=150)
        self.speed_scale.set(self.speed)
        self.speed_scale.pack(side=tk.LEFT, padx=5)
        
        # فریم اطلاعات
        info_frame = tk.Frame(self.root, bg='#f0f0f0', padx=10, pady=5)
        info_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.info_label = tk.Label(info_frame, text="", bg='#f0f0f0', 
                                   font=('Arial', 11), justify=tk.LEFT)
        self.info_label.pack(side=tk.LEFT)
        
        # فریم شبیه‌سازی
        sim_frame = tk.Frame(self.root, bg='white')
        sim_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # کانواس برای نمایش ساختمان
        self.canvas = tk.Canvas(sim_frame, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(sim_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.draw_building()
    
    def draw_building(self):
        """رسم ساختمان و آسانسور"""
        self.canvas.delete("all")
        
        width = 800
        floor_height = 50
        total_height = self.building.num_floors * floor_height
        
        self.canvas.config(scrollregion=(0, 0, width, total_height))
        
        elevator_floor = self.building.elevator.current_floor
        elevator_x = 150
        
        # رسم طبقات (از بالا به پایین)
        for i in range(self.building.num_floors - 1, -1, -1):
            y = (self.building.num_floors - 1 - i) * floor_height
            
            # خط طبقه
            self.canvas.create_rectangle(50, y, width - 50, y + floor_height,
                                        outline='black', fill='#f5f5f5', width=2)
            
            # شماره طبقه
            self.canvas.create_text(80, y + 25, text=f"طبقه {i}",
                                  font=('Arial', 12, 'bold'))
            
            # مسافران منتظر
            waiting = self.building.floors[i].waiting_people
            if waiting:
                wait_text = f"منتظر: {len(waiting)}"
                self.canvas.create_text(250, y + 25, text=wait_text,
                                      font=('Arial', 10), fill='blue')
            
            # آسانسور در این طبقه
            if i == elevator_floor:
                # جعبه آسانسور
                self.canvas.create_rectangle(elevator_x - 30, y + 5, elevator_x + 30, y + 45,
                                            fill='#FF9800', outline='black', width=3)
                
                # تعداد مسافران داخل
                passengers_text = f"{len(self.building.elevator.passengers)}/{self.building.elevator.capacity}"
                self.canvas.create_text(elevator_x, y + 25, text=passengers_text,
                                      font=('Arial', 12, 'bold'), fill='white')
                
                # جهت حرکت
                direction = self.building.elevator.direction
                if direction == Direction.UP:
                    self.canvas.create_text(elevator_x + 50, y + 25, text="↑",
                                          font=('Arial', 20), fill='green')
                elif direction == Direction.DOWN:
                    self.canvas.create_text(elevator_x + 50, y + 25, text="↓",
                                          font=('Arial', 20), fill='red')
        
        # به‌روزرسانی اطلاعات
        info = f"زمان: {self.building.time} | "
        info += f"طبقه آسانسور: {elevator_floor} | "
        info += f"مسافران داخل: {len(self.building.elevator.passengers)} | "
        info += f"جهت: {self.building.elevator.direction.name} | "
        info += f"مسافت کل: {self.building.elevator.total_distance}"
        
        self.info_label.config(text=info)
    
    def add_person_ui(self):
        """افزودن مسافر از رابط کاربری"""
        try:
            current = int(self.current_floor_entry.get())
            dest = int(self.dest_floor_entry.get())
            
            if current == dest:
                tk.messagebox.showwarning("خطا", "طبقه فعلی و مقصد نمی‌توانند یکسان باشند!")
                return
            
            person = self.building.add_person_request(current, dest)
            if person:
                self.draw_building()
            else:
                tk.messagebox.showerror("خطا", "طبقه نامعتبر!")
        except ValueError:
            tk.messagebox.showerror("خطا", "لطفا عدد وارد کنید!")
    
    def toggle_simulation(self):
        """شروع/توقف شبیه‌سازی"""
        self.running = not self.running
        if self.running:
            self.start_button.config(text="توقف", bg='#f44336')
            self.run_simulation()
        else:
            self.start_button.config(text="شروع", bg='#2196F3')
    
    def run_simulation(self):
        """اجرای شبیه‌سازی"""
        if self.running:
            self.building.step()
            self.draw_building()
            self.root.after(self.speed, self.run_simulation)
    
    def change_speed(self, value):
        """تغییر سرعت شبیه‌سازی"""
        self.speed = int(value)
    
    def run(self):
        """اجرای برنامه"""
        self.root.mainloop()

# اجرای برنامه
if __name__ == "__main__":
    # شماره دانشجویی: 03220040709006
    # آخرین رقم غیرصفر: 6
    a = 6
    num_floors = 10 * a  # 60 طبقه
    
    building = Building(num_floors)
    
    # افزودن چند مسافر تستی
    building.add_person_request(0, 25)
    building.add_person_request(5, 40)
    building.add_person_request(30, 10)
    
    gui = GUI(building)
    gui.run()
