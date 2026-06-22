"""
پروژه 2: شبیه‌ساز چراغ راهنمایی هوشمند
شماره دانشجویی: 03220040709006
a = 6
"""

import tkinter as tk
from tkinter import ttk
from collections import deque
from enum import Enum
import random

# ──────────────────────────────────────────
# Enums
# ──────────────────────────────────────────
class LightState(Enum):
    RED    = "red"
    YELLOW = "yellow"
    GREEN  = "green"

class Direction(Enum):
    NORTH = 0
    EAST  = 1
    SOUTH = 2
    WEST  = 3

# ──────────────────────────────────────────
# Car
# ──────────────────────────────────────────
class Car:
    _id_counter = 0

    def __init__(self, direction: Direction):
        Car._id_counter += 1
        self.id        = Car._id_counter
        self.direction = direction
        self.wait_time = 0

    def tick(self):
        self.wait_time += 1

    def __repr__(self):
        return f"Car({self.id}, dir={self.direction.name}, wait={self.wait_time}s)"

# ──────────────────────────────────────────
# TrafficLight
# ──────────────────────────────────────────
class TrafficLight:
    def __init__(self, direction: Direction, green_duration: int = 10,
                 yellow_duration: int = 3, red_duration: int = 10):
        self.direction        = direction
        self.state            = LightState.RED
        self.green_duration   = green_duration
        self.yellow_duration  = yellow_duration
        self.red_duration     = red_duration
        self.remaining        = red_duration

    def set_state(self, state: LightState, duration: int):
        self.state     = state
        self.remaining = duration

    def tick(self) -> bool:
        """Returns True when timer expires."""
        self.remaining -= 1
        return self.remaining <= 0

    def is_green(self) -> bool:
        return self.state == LightState.GREEN

    def color(self) -> str:
        return self.state.value

# ──────────────────────────────────────────
# Lane
# ──────────────────────────────────────────
class Lane:
    def __init__(self, direction: Direction):
        self.direction  = direction
        self.queue: deque[Car] = deque()
        self.light      = TrafficLight(direction)
        self.total_passed = 0
        self.total_wait   = 0

    def add_car(self) -> Car:
        car = Car(self.direction)
        self.queue.append(car)
        return car

    def release_car(self) -> Car | None:
        """Release front car if light is green."""
        if self.light.is_green() and self.queue:
            car = self.queue.popleft()
            self.total_passed += 1
            self.total_wait   += car.wait_time
            return car
        return None

    def tick_waiting_cars(self):
        for car in self.queue:
            car.tick()

    def queue_length(self) -> int:
        return len(self.queue)

    def avg_wait(self) -> float:
        if self.total_passed == 0:
            return 0.0
        return self.total_wait / self.total_passed

# ──────────────────────────────────────────
# Controller  (adaptive scheduling)
# ──────────────────────────────────────────
class Controller:
    """
    الگوریتم زمان‌بندی تطبیقی:
    - طولانی‌ترین صف اولویت بالاتری برای سبز شدن دارد
    - زمان سبز متناسب با طول صف تعیین می‌شود
    """
    BASE_GREEN  = 8
    MAX_GREEN   = 20
    YELLOW_DUR  = 3

    def __init__(self, lanes: dict[Direction, Lane]):
        self.lanes          = lanes
        self.current_green  : Direction | None = None
        self.phase_timer    = 0
        self.in_yellow      = False

    def _choose_next(self) -> Direction:
        """Choose lane with the longest queue."""
        return max(self.lanes, key=lambda d: self.lanes[d].queue_length())

    def _green_duration(self, direction: Direction) -> int:
        q = self.lanes[direction].queue_length()
        return min(self.BASE_GREEN + q, self.MAX_GREEN)

    def _set_all_red(self):
        for lane in self.lanes.values():
            lane.light.set_state(LightState.RED, 999)

    def start(self):
        direction = self._choose_next()
        self._set_all_red()
        dur = self._green_duration(direction)
        self.lanes[direction].light.set_state(LightState.GREEN, dur)
        self.current_green = direction
        self.phase_timer   = dur
        self.in_yellow     = False

    def tick(self):
        if self.current_green is None:
            self.start()
            return

        self.phase_timer -= 1

        if self.phase_timer <= 0:
            if not self.in_yellow:
                # green → yellow
                self.lanes[self.current_green].light.set_state(
                    LightState.YELLOW, self.YELLOW_DUR)
                self.phase_timer = self.YELLOW_DUR
                self.in_yellow   = True
            else:
                # yellow → next green
                self.lanes[self.current_green].light.set_state(
                    LightState.RED, 999)
                nxt = self._choose_next()
                dur = self._green_duration(nxt)
                self.lanes[nxt].light.set_state(LightState.GREEN, dur)
                self.current_green = nxt
                self.phase_timer   = dur
                self.in_yellow     = False

# ──────────────────────────────────────────
# Intersection
# ──────────────────────────────────────────
class Intersection:
    def __init__(self, a: int = 6):
        self.a          = a
        self.time       = 0
        # spawn interval: every a seconds a random car arrives
        self.spawn_interval = max(1, a)

        self.lanes: dict[Direction, Lane] = {
            d: Lane(d) for d in Direction
        }
        self.controller = Controller(self.lanes)
        self.controller.start()

    def step(self):
        self.time += 1

        # Spawn cars periodically (random lane)
        if self.time % self.spawn_interval == 0:
            d = random.choice(list(Direction))
            self.lanes[d].add_car()

        # Tick controller (light phase management)
        self.controller.tick()

        # Release one car per green lane per step & update wait times
        for lane in self.lanes.values():
            lane.tick_waiting_cars()
            if lane.light.is_green():
                lane.release_car()

    def stats(self) -> dict:
        return {
            d.name: {
                "queue"    : lane.queue_length(),
                "light"    : lane.light.state.name,
                "remaining": lane.light.remaining,
                "passed"   : lane.total_passed,
                "avg_wait" : round(lane.avg_wait(), 1),
            }
            for d, lane in self.lanes.items()
        }

# ──────────────────────────────────────────
# GUI
# ──────────────────────────────────────────
class GUI:
    CANVAS_SIZE = 520
    CENTER      = 260
    ROAD_WIDTH  = 60
    CAR_SIZE    = 10

    # lane label positions (x, y)
    LANE_LABEL = {
        Direction.NORTH: (260, 80),
        Direction.SOUTH: (260, 440),
        Direction.EAST : (440, 260),
        Direction.WEST : (80,  260),
    }

    # light positions
    LIGHT_POS = {
        Direction.NORTH: (210, 195),
        Direction.SOUTH: (310, 325),
        Direction.EAST : (325, 210),
        Direction.WEST : (195, 310),
    }

    # car queue draw origins & axis
    QUEUE_CONFIG = {
        Direction.NORTH: {"origin": (255, 185), "dx": 0,  "dy": -14},
        Direction.SOUTH: {"origin": (265, 335), "dx": 0,  "dy":  14},
        Direction.EAST : {"origin": (335, 255), "dx": 14, "dy":   0},
        Direction.WEST : {"origin": (185, 265), "dx":-14, "dy":   0},
    }

    def __init__(self, root: tk.Tk, intersection: Intersection):
        self.root         = root
        self.intersection = intersection
        self.running      = False
        self.speed        = 500  # ms per step

        root.title("شبیه‌ساز چراغ راهنمایی هوشمند  |  a=6")
        root.resizable(False, False)

        self._build_ui()
        self._draw_static()

    # ── UI layout ──────────────────────────
    def _build_ui(self):
        top = tk.Frame(self.root, bg="#1e1e2e", padx=6, pady=4)
        top.pack(fill=tk.X)

        tk.Label(top, text="شبیه‌ساز چراغ راهنمایی هوشمند",
                 font=("Tahoma", 13, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side=tk.LEFT)

        tk.Label(top, text="a = 6  |  شماره دانشجویی: 03220040709006",
                 font=("Tahoma", 9), bg="#1e1e2e", fg="#a6adc8").pack(side=tk.RIGHT)

        # Main area
        main = tk.Frame(self.root, bg="#181825")
        main.pack(fill=tk.BOTH, expand=True)

        # Canvas
        self.canvas = tk.Canvas(main, width=self.CANVAS_SIZE,
                                height=self.CANVAS_SIZE, bg="#181825",
                                highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=8, pady=8)

        # Right panel
        right = tk.Frame(main, bg="#181825", width=220)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=8)
        right.pack_propagate(False)

        # ── controls ──
        ctrl = tk.LabelFrame(right, text=" کنترل ", bg="#181825",
                             fg="#cdd6f4", font=("Tahoma", 9, "bold"))
        ctrl.pack(fill=tk.X, pady=4)

        btn_frame = tk.Frame(ctrl, bg="#181825")
        btn_frame.pack(pady=4)

        self.btn_start = tk.Button(btn_frame, text="▶  شروع",
                                   command=self._toggle,
                                   bg="#a6e3a1", fg="#1e1e2e",
                                   font=("Tahoma", 9, "bold"), width=9)
        self.btn_start.pack(side=tk.LEFT, padx=3)

        tk.Button(btn_frame, text="↺  ریست",
                  command=self._reset,
                  bg="#f38ba8", fg="#1e1e2e",
                  font=("Tahoma", 9, "bold"), width=9).pack(side=tk.LEFT, padx=3)

        tk.Label(ctrl, text="سرعت شبیه‌سازی",
                 bg="#181825", fg="#cdd6f4",
                 font=("Tahoma", 8)).pack()
        self.speed_var = tk.IntVar(value=500)
        tk.Scale(ctrl, from_=100, to=1500, orient=tk.HORIZONTAL,
                 variable=self.speed_var, bg="#181825", fg="#cdd6f4",
                 troughcolor="#313244", highlightthickness=0,
                 command=self._on_speed).pack(fill=tk.X, padx=6)

        # ── manual add car ──
        add_frame = tk.LabelFrame(right, text=" افزودن خودرو ",
                                  bg="#181825", fg="#cdd6f4",
                                  font=("Tahoma", 9, "bold"))
        add_frame.pack(fill=tk.X, pady=4)

        self.dir_var = tk.StringVar(value="NORTH")
        for d in Direction:
            label_map = {"NORTH":"شمال","SOUTH":"جنوب",
                         "EAST":"شرق","WEST":"غرب"}
            tk.Radiobutton(add_frame, text=label_map[d.name],
                           variable=self.dir_var, value=d.name,
                           bg="#181825", fg="#cdd6f4",
                           selectcolor="#313244",
                           font=("Tahoma", 8)).pack(anchor=tk.W, padx=8)

        tk.Button(add_frame, text="+ افزودن خودرو",
                  command=self._add_car_manual,
                  bg="#89b4fa", fg="#1e1e2e",
                  font=("Tahoma", 9, "bold")).pack(pady=4, padx=6, fill=tk.X)

        # ── stats ──
        stats_frame = tk.LabelFrame(right, text=" آمار ",
                                    bg="#181825", fg="#cdd6f4",
                                    font=("Tahoma", 9, "bold"))
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        self.stats_text = tk.Text(stats_frame, bg="#181825", fg="#cdd6f4",
                                  font=("Courier", 8), state=tk.DISABLED,
                                  relief=tk.FLAT, height=14)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # status bar
        self.status_var = tk.StringVar(value="زمان: 0 ثانیه")
        tk.Label(self.root, textvariable=self.status_var,
                 bg="#313244", fg="#cdd6f4",
                 font=("Tahoma", 9), anchor=tk.W).pack(
                     fill=tk.X, side=tk.BOTTOM)

    # ── static road drawing ────────────────
    def _draw_static(self):
        C  = self.CENTER
        RW = self.ROAD_WIDTH
        S  = self.CANVAS_SIZE

        # background
        self.canvas.create_rectangle(0, 0, S, S, fill="#1e1e2e", outline="")

        # roads (horizontal & vertical)
        self.canvas.create_rectangle(0, C-RW, S, C+RW,
                                     fill="#45475a", outline="")
        self.canvas.create_rectangle(C-RW, 0, C+RW, S,
                                     fill="#45475a", outline="")

        # center intersection box
        self.canvas.create_rectangle(C-RW, C-RW, C+RW, C+RW,
                                     fill="#585b70", outline="")

        # dashed center lines
        for x in range(0, C-RW, 30):
            self.canvas.create_line(x, C, x+15, C,
                                    fill="#f5c2e7", dash=(6,4), width=1)
        for x in range(C+RW, S, 30):
            self.canvas.create_line(x, C, x+15, C,
                                    fill="#f5c2e7", dash=(6,4), width=1)
        for y in range(0, C-RW, 30):
            self.canvas.create_line(C, y, C, y+15,
                                    fill="#f5c2e7", dash=(6,4), width=1)
        for y in range(C+RW, S, 30):
            self.canvas.create_line(C, y, C, y+15,
                                    fill="#f5c2e7", dash=(6,4), width=1)

        # direction labels
        labels = {"شمال":(C, 20), "جنوب":(C, S-20),
                  "شرق":(S-20, C), "غرب":(20, C)}
        for txt, (x, y) in labels.items():
            self.canvas.create_text(x, y, text=txt, fill="#cdd6f4",
                                    font=("Tahoma", 9, "bold"))

    # ── dynamic drawing ────────────────────
    def _draw_dynamic(self):
        # remove all dynamic items
        self.canvas.delete("dynamic")

        stats = self.intersection.stats()
        C     = self.CENTER
        RW    = self.ROAD_WIDTH

        for direction, lane in self.intersection.lanes.items():
            d_name = direction.name
            lx, ly = self.LIGHT_POS[direction]

            # traffic light circle
            color  = lane.light.color()
            outline_clr = "#ffffff" if lane.light.is_green() else "#555577"
            self.canvas.create_oval(lx-10, ly-10, lx+10, ly+10,
                                    fill=color, outline=outline_clr,
                                    width=2, tags="dynamic")

            # remaining seconds on light
            self.canvas.create_text(lx, ly,
                                    text=str(max(0, lane.light.remaining)),
                                    fill="#1e1e2e",
                                    font=("Tahoma", 7, "bold"),
                                    tags="dynamic")

            # draw queued cars
            cfg = self.QUEUE_CONFIG[direction]
            ox, oy   = cfg["origin"]
            dx, dy   = cfg["dx"],  cfg["dy"]
            cs = self.CAR_SIZE

            for i, car in enumerate(list(lane.queue)[:8]):
                cx = ox + dx * i
                cy = oy + dy * i
                self.canvas.create_rectangle(
                    cx - cs//2, cy - cs//2,
                    cx + cs//2, cy + cs//2,
                    fill="#89b4fa", outline="#1e1e2e",
                    tags="dynamic")

            # queue count label
            qlx, qly = self.LANE_LABEL[direction]
            self.canvas.create_text(
                qlx, qly,
                text=f"صف: {lane.queue_length()}  |  گذشته: {lane.total_passed}",
                fill="#a6e3a1", font=("Tahoma", 8, "bold"),
                tags="dynamic")

        # center time display
        self.canvas.create_text(
            C, C, text=f"t={self.intersection.time}",
            fill="#cdd6f4", font=("Tahoma", 10, "bold"),
            tags="dynamic")

        # update stats panel
        self._update_stats(stats)

    def _update_stats(self, stats: dict):
        lines = [f"زمان: {self.intersection.time} ثانیه\n"]
        dir_fa = {"NORTH":"شمال","SOUTH":"جنوب",
                  "EAST":"شرق","WEST":"غرب"}
        for d, s in stats.items():
            lines.append(
                f"{dir_fa[d]}:\n"
                f"  چراغ : {s['light']:6}  ({s['remaining']}s)\n"
                f"  صف   : {s['queue']}\n"
                f"  گذشته: {s['passed']}\n"
                f"  میانگین انتظار: {s['avg_wait']}s\n"
            )
        text = "\n".join(lines)
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state=tk.DISABLED)

        self.status_var.set(f"زمان: {self.intersection.time} ثانیه  |  "
                            f"در صف: "
                            f"{sum(s['queue'] for s in stats.values())} خودرو")

    # ── controls ──────────────────────────
    def _toggle(self):
        self.running = not self.running
        self.btn_start.config(
            text="⏸  توقف" if self.running else "▶  شروع",
            bg="#f38ba8" if self.running else "#a6e3a1")
        if self.running:
            self._loop()

    def _loop(self):
        if not self.running:
            return
        self.intersection.step()
        self._draw_dynamic()
        self.speed = self.speed_var.get()
        self.root.after(self.speed, self._loop)

    def _reset(self):
        self.running = False
        self.btn_start.config(text="▶  شروع", bg="#a6e3a1")
        Car._id_counter = 0
        self.intersection.__init__(a=6)
        self._draw_static()
        self._draw_dynamic()

    def _add_car_manual(self):
        d = Direction[self.dir_var.get()]
        self.intersection.lanes[d].add_car()
        self._draw_dynamic()

    def _on_speed(self, _=None):
        self.speed = self.speed_var.get()


# ──────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────
def main():
    a            = 6                          # آخرین رقم غیرصفر شماره دانشجویی
    student_id   = "03220040709006"

    intersection = Intersection(a=a)

    # چند خودروی اولیه برای تست
    intersection.lanes[Direction.NORTH].add_car()
    intersection.lanes[Direction.NORTH].add_car()
    intersection.lanes[Direction.EAST].add_car()
    intersection.lanes[Direction.WEST].add_car()
    intersection.lanes[Direction.WEST].add_car()
    intersection.lanes[Direction.WEST].add_car()
    intersection.lanes[Direction.SOUTH].add_car()

    root = tk.Tk()
    app  = GUI(root, intersection)
    app._draw_dynamic()
    root.mainloop()


if __name__ == "__main__":
    main()
