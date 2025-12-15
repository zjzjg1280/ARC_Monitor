import tkinter as tk
import tkinter.font as tkfont
import requests
import threading
import time
import ctypes
from datetime import datetime, timezone, timedelta

# ================= DPI 修复 (防止模糊) =================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
# ======================================================

# 配置
REAL_API_URL = "https://metaforge.app/api/arc-raiders/event-timers"
REFRESH_INTERVAL = 60

# 翻译字典
TRANSLATIONS = {
    "Buried City": "掩埋废都", "Dam": "大坝", "Spaceport": "航天港",
    "Blue Gate": "蓝门", "Stella Montis": "斯特拉山", "City": "城市",
    "Electromagnetic Storm": "电磁风暴", "Harvester": "收割者",
    "Lush Blooms": "繁花异变", "Matriarch": "母体",
    "Night Raid": "夜袭", "Roaming BT": "游荡BT",
    "Uplink": "数据上行", "Supply Drop": "补给投放",
    "Uncovered Caches": "暴露的奇袭者箱", "Launch Tower Loot": "发射塔战利品"
}


class ArcEventWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Arc Raiders Events")

        # --- 窗口设置 ---
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 0.9)
        self.root.configure(bg='#1e1e1e')
        self.root.geometry("220x780+100+100")

        # --- 字体 ---
        self.font_size = 10
        self.font_title = tkfont.Font(family="微软雅黑", size=self.font_size + 2, weight="bold")
        self.font_content = tkfont.Font(family="Consolas", size=self.font_size)
        self.font_card_header = tkfont.Font(family="微软雅黑", size=self.font_size + 1, weight="bold")

        self.current_data_list = []

        # --- 标题栏 ---
        self.header_frame = tk.Frame(root, bg="#2d2d2d", cursor="fleur")
        self.header_frame.pack(fill="x", ipady=5)

        self.title_label = tk.Label(self.header_frame, text="Arc Raiders 监控",
                                    font=self.font_title, bg="#2d2d2d", fg="#00ffcc")
        self.title_label.pack(side="left", padx=10)

        self.close_btn = tk.Button(self.header_frame, text="×", command=root.quit,
                                   bg="#ff4444", fg="white", bd=0,
                                   font=("Arial", 10, "bold"), width=3)
        self.close_btn.pack(side="right", padx=5)

        # --- 内容容器 ---
        self.main_container = tk.Frame(root, bg="#1e1e1e")
        self.main_container.pack(fill="both", expand=True)

        self.cards_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        self.cards_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # --- 缩放手柄 ---
        self.resize_grip = tk.Label(root, text="◢", bg="#1e1e1e", fg="#666666",
                                    font=("Arial", 12), cursor="sizing")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")

        # --- 绑定事件 ---
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
        self.header_frame.bind("<Button-1>", self.start_move)
        self.header_frame.bind("<B1-Motion>", self.do_move)

        self.resize_grip.bind("<Button-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.do_resize)

        self.root.bind("<Configure>", self.on_window_resize)
        self.root.bind("<Control-MouseWheel>", self.do_zoom_text)

        self.update_data_loop()

    # === 窗口逻辑 ===
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_w = self.root.winfo_width()
        self.start_h = self.root.winfo_height()

    def do_resize(self, event):
        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y
        new_w = max(self.start_w + dx, 250)
        new_h = max(self.start_h + dy, 200)
        self.root.geometry(f"{new_w}x{new_h}")

    def on_window_resize(self, event):
        if event.widget == self.root:
            self.refresh_layout()

    def refresh_layout(self):
        if not self.current_data_list: return
        for widget in self.cards_frame.winfo_children():
            widget.grid_forget()

        window_width = self.root.winfo_width()
        card_min_width = 220
        columns = max(1, window_width // card_min_width)

        for i, card_data in enumerate(self.current_data_list):
            row = i // columns
            col = i % columns

            card = tk.Frame(self.cards_frame, bg="#252526", bd=1, relief="ridge")
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            tk.Label(card, text=f"📍 {card_data['location']}",
                     font=self.font_card_header, bg="#252526", fg="#ffffff", anchor="w") \
                .pack(fill="x", padx=5, pady=2)
            tk.Frame(card, bg="#444", height=1).pack(fill="x")

            tk.Label(card, text=card_data['text'],
                     font=self.font_content, bg="#252526", fg="#e0e0e0",
                     justify="left", anchor="nw").pack(fill="both", expand=True, padx=5, pady=5)

        for c in range(columns):
            self.cards_frame.columnconfigure(c, weight=1)

    def do_zoom_text(self, event):
        delta = 1 if event.delta > 0 else -1
        self.font_size += delta
        if self.font_size < 8: self.font_size = 8
        if self.font_size > 20: self.font_size = 20
        self.font_content.configure(size=self.font_size)
        self.font_card_header.configure(size=self.font_size + 1)
        self.font_title.configure(size=self.font_size + 2)

    # === 数据逻辑 ===
    def fetch_data(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(REAL_API_URL, headers=headers, timeout=10)
            if response.status_code != 200: return []
            data = response.json()

            events_list = []
            if isinstance(data, list):
                events_list = data
            elif isinstance(data, dict):
                for k in ["data", "items", "timers", "events"]:
                    if k in data and isinstance(data[k], list):
                        events_list = data[k];
                        break
                if not events_list: events_list = [v for v in data.values() if isinstance(v, dict)]

            if not events_list: return []

            now = datetime.now(timezone.utc)
            today_str = now.strftime('%Y-%m-%d')
            tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
            grouped = {}
            for item in events_list:
                raw_name = item.get("name") or item.get("title") or "Unknown"
                raw_loc = item.get("map") or item.get("maps") or item.get("location") or "Unknown"
                if isinstance(raw_loc, list): raw_loc = ", ".join(raw_loc)
                cn_name = TRANSLATIONS.get(raw_name, raw_name)
                cn_loc = TRANSLATIONS.get(raw_loc, raw_loc)
                schedule = []
                for k, v in item.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "start" in v[0]:
                        schedule = v;
                        break
                if schedule:
                    if cn_loc not in grouped: grouped[cn_loc] = []
                    grouped[cn_loc].append({"name": cn_name, "schedule": schedule})

            structured_result = []
            for location, items in grouped.items():
                loc_text = ""
                processed_items = []
                for event in items:
                    name, schedule = event["name"], event["schedule"]
                    time_slots = []
                    for day_str in [today_str, tomorrow_str]:
                        for slot in schedule:
                            if not (slot.get("start") and slot.get("end")): continue
                            try:
                                s_dt = datetime.strptime(f"{day_str} {slot['start']} +0000", '%Y-%m-%d %H:%M %z')
                                e_dt = datetime.strptime(f"{day_str} {slot['end']} +0000", '%Y-%m-%d %H:%M %z')
                                if e_dt < s_dt: e_dt += timedelta(days=1)
                                time_slots.append((s_dt, e_dt))
                            except:
                                continue
                    time_slots.sort(key=lambda x: x[0])
                    found_active = False
                    for start, end in time_slots:
                        if start <= now <= end:
                            mm, ss = divmod((end - now).seconds, 60)
                            hh, mm = divmod(mm, 60)
                            t_str = f"{hh}:{mm:02d}" if hh > 0 else f"{mm}分{ss}秒"
                            processed_items.append({"p": 0, "t": start, "txt": f"🟢 {name}\n   ⏳ {t_str}\n"})
                            found_active = True;
                            break
                    if not found_active:
                        future = [s for s in time_slots if s[0] > now]
                        if future:
                            wait = future[0][0] - now
                            mm, ss = divmod(wait.seconds, 60)
                            hh, mm = divmod(mm, 60)
                            w_str = f"{hh}:{mm:02d}" if hh > 0 else f"{mm}分"
                            processed_items.append({"p": 1, "t": future[0][0], "txt": f"⚪ {name}\n   🔜 {w_str}\n"})

                processed_items.sort(key=lambda x: (x["p"], x["t"]))
                if processed_items:
                    for p in processed_items: loc_text += p["txt"]
                else:
                    loc_text = "(暂无活动)"
                structured_result.append({"location": location, "text": loc_text.strip()})
            return structured_result

        except Exception as e:
            return []

    def update_ui(self, data_list):
        if not data_list: return
        self.current_data_list = data_list
        self.refresh_layout()

    def worker(self):
        data = self.fetch_data()
        self.root.after(0, self.update_ui, data)
        self.root.after(REFRESH_INTERVAL * 1000, self.update_data_loop)

    def update_data_loop(self):
        threading.Thread(target=self.worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ArcEventWidget(root)
    root.mainloop()