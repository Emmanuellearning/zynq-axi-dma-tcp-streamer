import socket
import struct
import tkinter as tk
from collections import deque

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

HOST = "192.168.1.10"
PORT = 7

WINDOW             = 500           # initial visible samples — change with the slider
UPDATE_MS          = 20
SAMPLES_PER_PACKET = 100
BYTES_PER_PACKET   = SAMPLES_PER_PACKET * 8   # 800 bytes

# ── Raw display buffers (no smoothing) ───────────────────────────────────────
buf1 = deque([0] * WINDOW, maxlen=WINDOW)
buf2 = deque([0] * WINDOW, maxlen=WINDOW)
buf3 = deque([0] * WINDOW, maxlen=WINDOW)
buf4 = deque([0] * WINDOW, maxlen=WINDOW)

# ── Socket ────────────────────────────────────────────────────────────────────
sock = socket.socket()
sock.connect((HOST, PORT))
sock.setblocking(False)

# ── Root window ───────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("FPGA 4-Channel Oscilloscope")

main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

plot_frame = tk.Frame(main_frame)
plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

ctrl_frame = tk.LabelFrame(main_frame, text="Controls", padx=10, pady=10)
ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig = Figure(figsize=(9, 6), dpi=100)

ax1 = fig.add_subplot(411)
ax2 = fig.add_subplot(412)
ax3 = fig.add_subplot(413)
ax4 = fig.add_subplot(414)

line1, = ax1.plot(list(buf1), linewidth=0.8)
line2, = ax2.plot(list(buf2), linewidth=0.8)
line3, = ax3.plot(list(buf3), linewidth=0.8)
line4, = ax4.plot(list(buf4), linewidth=0.8)

for ax, name in zip([ax1, ax2, ax3, ax4],
                    ["CH1", "CH2", "CH3", "CH4"]):
    ax.set_ylim(-33000, 33000)
    ax.set_xlim(0, WINDOW)
    ax.grid(True)
    ax.set_title(name, fontsize=9)

fig.tight_layout()
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
canvas.draw()

# ── Pause / Resume ────────────────────────────────────────────────────────────
running = True

def toggle():
    global running
    running = not running
    btn.config(text="Resume" if not running else "Pause")

btn = tk.Button(plot_frame, text="Pause", command=toggle)
btn.pack(pady=4)

# ── Frequency send ────────────────────────────────────────────────────────────
# Reads the entry boxes only — sliders and entry boxes are fully independent.
# Send is triggered by: Send button, Enter key in entry, or slider release.
status_var = tk.StringVar(value="Not sent yet")

def send_freq(event=None):
    try:
        f0 = max(0, min(65535, int(freq0_var.get())))
        f1 = max(0, min(65535, int(freq1_var.get())))
    except ValueError:
        status_var.set("Invalid input — enter integers 0-65535")
        return
    try:
        sock.sendall(struct.pack('<HH', f0, f1))
        status_var.set(f"Sent  C0=0x{f0:04X}  C1=0x{f1:04X}")
    except Exception as e:
        status_var.set(f"Send error: {e}")

# ── CORDIC 0 ──────────────────────────────────────────────────────────────────
tk.Label(ctrl_frame, text="CORDIC Frequency Control",
         font=("Arial", 11, "bold")).pack(pady=(0, 6))

tk.Label(ctrl_frame, text="CORDIC 0", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Label(ctrl_frame, text="Frequency word (0-65535):").pack(anchor="w")
freq0_var = tk.StringVar(value="0")
freq0_entry = tk.Entry(ctrl_frame, textvariable=freq0_var, width=10)
freq0_entry.pack(anchor="w", pady=(0, 4))
freq0_entry.bind("<Return>", send_freq)   # Enter key sends

# Slider moves independently — releases trigger a send using whatever is in the entry box
freq0_slider = tk.Scale(ctrl_frame, from_=0, to=65535,
                        orient=tk.HORIZONTAL, length=180)
freq0_slider.pack()

def on_freq0_release(event):
    freq0_var.set(str(freq0_slider.get()))   # copy slider → entry only on release
    send_freq()

freq0_slider.bind("<ButtonRelease-1>", on_freq0_release)

tk.Frame(ctrl_frame, height=2, bg="grey").pack(fill=tk.X, pady=8)

# ── CORDIC 1 ──────────────────────────────────────────────────────────────────
tk.Label(ctrl_frame, text="CORDIC 1", font=("Arial", 10, "bold")).pack(anchor="w")
tk.Label(ctrl_frame, text="Frequency word (0-65535):").pack(anchor="w")
freq1_var = tk.StringVar(value="0")
freq1_entry = tk.Entry(ctrl_frame, textvariable=freq1_var, width=10)
freq1_entry.pack(anchor="w", pady=(0, 4))
freq1_entry.bind("<Return>", send_freq)   # Enter key sends

freq1_slider = tk.Scale(ctrl_frame, from_=0, to=65535,
                        orient=tk.HORIZONTAL, length=180)
freq1_slider.pack()

def on_freq1_release(event):
    freq1_var.set(str(freq1_slider.get()))   # copy slider → entry only on release
    send_freq()

freq1_slider.bind("<ButtonRelease-1>", on_freq1_release)

tk.Frame(ctrl_frame, height=2, bg="grey").pack(fill=tk.X, pady=8)

# ── Window size ───────────────────────────────────────────────────────────────
# Fewer samples = fewer cycles on screen = clearer waveform
tk.Label(ctrl_frame, text="Window Size (samples)",
         font=("Arial", 10, "bold")).pack(anchor="w")
tk.Label(ctrl_frame, text="(smaller = zoom in, clearer sine)").pack(anchor="w")
window_var = tk.IntVar(value=WINDOW)

def apply_window_change(event=None):
    global buf1, buf2, buf3, buf4
    n = max(100, window_var.get())
    def resize(old, new_n):
        data = list(old)
        if len(data) < new_n:
            data = [0] * (new_n - len(data)) + data
        return deque(data[-new_n:], maxlen=new_n)
    buf1 = resize(buf1, n)
    buf2 = resize(buf2, n)
    buf3 = resize(buf3, n)
    buf4 = resize(buf4, n)
    xdata = list(range(n))
    line1.set_xdata(xdata); line1.set_ydata(list(buf1))
    line2.set_xdata(xdata); line2.set_ydata(list(buf2))
    line3.set_xdata(xdata); line3.set_ydata(list(buf3))
    line4.set_xdata(xdata); line4.set_ydata(list(buf4))
    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_xlim(0, n)
    canvas.draw()

window_slider = tk.Scale(ctrl_frame, from_=100, to=5000, resolution=100,
                         orient=tk.HORIZONTAL, length=180,
                         variable=window_var)
window_slider.pack()
window_slider.bind("<ButtonRelease-1>", apply_window_change)  # only fires once on release


# ── Trigger ───────────────────────────────────────────────────────────────────
tk.Label(ctrl_frame, text="Trigger", font=("Arial", 10, "bold")).pack(anchor="w")
trigger_on_var = tk.BooleanVar(value=False)
tk.Checkbutton(ctrl_frame, text="Enable (CH1 rising edge)",
               variable=trigger_on_var).pack(anchor="w")

tk.Frame(ctrl_frame, height=2, bg="grey").pack(fill=tk.X, pady=8)

# ── Send button ───────────────────────────────────────────────────────────────
tk.Button(ctrl_frame, text="Send Frequency",
          command=send_freq,
          bg="#4CAF50", fg="white",
          font=("Arial", 10, "bold"),
          width=18).pack(pady=6)
tk.Label(ctrl_frame, textvariable=status_var, wraplength=180, fg="blue").pack()

# ── Receive buffer ────────────────────────────────────────────────────────────
recv_raw = bytearray()

def signed16(v):
    return v - 65536 if v >= 32768 else v

# Trigger: track previous CH1 sample for edge detection
_prev_ch1 = 0

def find_trigger(ch1_samples, level):
    """Return index of first rising-edge crossing at 'level', or -1."""
    global _prev_ch1
    prev = _prev_ch1
    for i, v in enumerate(ch1_samples):
        if prev < level <= v:
            _prev_ch1 = v
            return i
        prev = v
    if ch1_samples:
        _prev_ch1 = ch1_samples[-1]
    return -1

# ── Scope update loop ─────────────────────────────────────────────────────────
def update_scope():
    global recv_raw

    new_data = False

    if running:
        # Drain everything in the socket this tick
        while True:
            try:
                chunk = sock.recv(65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            recv_raw.extend(chunk)

        trig_on = trigger_on_var.get()

        s1_tick, s2_tick, s3_tick, s4_tick = [], [], [], []

        mv  = memoryview(recv_raw)
        off = 0
        while (off + BYTES_PER_PACKET) <= len(recv_raw):
            samples = struct.unpack_from("<100Q", mv, off)
            off += BYTES_PER_PACKET
            new_data = True
            for sample in samples:
                s1_tick.append(signed16( sample        & 0xFFFF))
                s2_tick.append(signed16((sample >> 16) & 0xFFFF))
                s3_tick.append(signed16((sample >> 32) & 0xFFFF))
                s4_tick.append(signed16((sample >> 48) & 0xFFFF))

        mv.release()             # must release before resizing the bytearray
        if off:
            del recv_raw[:off]   # discard consumed bytes

        if new_data:
            s1 = s1_tick
            s2 = s2_tick
            s3 = s3_tick
            s4 = s4_tick

            # Trigger — find phase-stable start point on CH1 rising edge
            if trig_on and s1:
                idx = find_trigger(s1, 0)
                if idx > 0:
                    s1 = s1[idx:]
                    s2 = s2[idx:]
                    s3 = s3[idx:]
                    s4 = s4[idx:]

            buf1.extend(s1)
            buf2.extend(s2)
            buf3.extend(s3)
            buf4.extend(s4)

            line1.set_ydata(list(buf1))
            line2.set_ydata(list(buf2))
            line3.set_ydata(list(buf3))
            line4.set_ydata(list(buf4))

            canvas.draw_idle()

    root.after(UPDATE_MS, update_scope)

update_scope()
root.mainloop()