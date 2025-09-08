import os
import subprocess
import threading
import platform
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import shutil
import mcrcon

#Directories 
BASE_DIR = os.path.join(os.path.expanduser("~"), "swapMine")
SERVERS_DIR = os.path.join(BASE_DIR, "servers")
os.makedirs(SERVERS_DIR, exist_ok=True)

#  Globals 
server_process = None

#Java Detection
JAVA_PATH = shutil.which("java")
if JAVA_PATH is None:
    # Ask user to locate java.exe
    root = tk.Tk()
    root.withdraw()  
    messagebox.showwarning("Java Not Found", "Java not found in PATH. Please select java.exe manually.")
    JAVA_PATH = filedialog.askopenfilename(title="Locate java.exe", filetypes=[("Java Executable", "java.exe")])
    if not JAVA_PATH:
        messagebox.showerror("Java Not Found", "No Java executable selected. Exiting.")
        exit()
    root.destroy()  

#Functions 
def find_servers():
    """Return {folder_name: path_to_first_jar}"""
    servers = {}
    for folder in os.listdir(SERVERS_DIR):
        folder_path = os.path.join(SERVERS_DIR, folder)
        if os.path.isdir(folder_path):
            jars = [f for f in os.listdir(folder_path) if f.lower().endswith(".jar")]
            if jars:
                servers[folder] = os.path.join(folder_path, jars[0])
    return servers

def append_console(text):
    console.config(state="normal")
    console.insert(tk.END, text)
    console.yview(tk.END)
    console.config(state="disabled")

def read_output():
    global server_process
    for line in server_process.stdout:
        append_console(line)
    server_process = None
    start_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED)

def start_server():
    global server_process
    selected = selected_server.get()
    if not selected:
        messagebox.showwarning("No Server", "Please select a server.")
        return
    jar_path = servers[selected]
    server_dir = os.path.dirname(jar_path)
    if server_process is not None:
        messagebox.showwarning("Server Running", "A server is already running!")
        return
    try:
        server_process = subprocess.Popen(
            [JAVA_PATH, "-Xmx1G", "-Xms1G", "-jar", jar_path, "nogui"],
            cwd=server_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start server:\n{e}")
        return
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)
    threading.Thread(target=read_output, daemon=True).start()

def stop_server():
    global server_process
    if rcon_enabled.get() and rcon_config["ip"]:
        send_command("stop")
        return

    if server_process and server_process.poll() is None:
        server_process.terminate()
        append_console("Server stopped.\n")
        start_btn.configure(state=tk.NORMAL)
        stop_btn.configure(state=tk.DISABLED)
    else:
        append_console("No server running.\n")

def send_command():
    cmd = command_entry.get()
    if not cmd:
        return

    if rcon_enabled.get() and rcon_config["ip"]:
        try:
            with Mcrcon(rcon_config["ip"], rcon_config["password"], port=rcon_config["port"]) as mcr:
                response = mcr.command(cmd)
                append_console(f"[RCON] {response}\n")
        except Exception as e:
            append_console(f"RCON error: {e}\n")
    else:
        if server_process and server_process.poll() is None:
            server_process.stdin.write(cmd + "\n")
            server_process.stdin.flush()
        else:
            append_console("No local server running.\n")

def open_folder(path):
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux and others
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Could not open folder: {e}")

def get_files():
    """Return a list of files in the directory."""
    return os.listdir(SERVERS_DIR)

def refresh():
    files = get_files()
    server_menu['values'] = files
    if files:
        server_menu.current(0)  # select first item automatically
    else:
        server_menu.set('')   




def configure_rcon():
    if not rcon_enabled.get():
        return  # Only configure if enabled

    config_win = tk.Toplevel(root)
    config_win.title("RCON Configuration")
    config_win.geometry("300x200")

    tk.Label(config_win, text="RCON IP:").pack(pady=5)
    ip_entry = tk.Entry(config_win)
    ip_entry.pack()

    tk.Label(config_win, text="RCON Port:").pack(pady=5)
    port_entry = tk.Entry(config_win)
    port_entry.insert(0, "25575")
    port_entry.pack()

    tk.Label(config_win, text="RCON Password:").pack(pady=5)
    pass_entry = tk.Entry(config_win, show="*")
    pass_entry.pack()

    def save_config():
        rcon_config["ip"] = ip_entry.get()
        rcon_config["port"] = int(port_entry.get())
        rcon_config["password"] = pass_entry.get()
        append_console(f"RCON configured: {rcon_config['ip']}:{rcon_config['port']}\n")
        config_win.destroy()

    tk.Button(config_win, text="Save", command=save_config).pack(pady=10)

# --- GUI ---
root = tk.Tk()
root.title("mineSwap")
root.geometry("700x500")
root.resizable(False, False)

rcon_enabled = tk.BooleanVar(value=False)
rcon_config = {"ip": "", "port": 25575, "password": ""}

# Console
console = scrolledtext.ScrolledText(root, width=80, height=20, state="disabled")
console.place(relx=".35",rely=".1",relwidth=".65",relheight=".5")

# Command entry
command_entry = tk.Entry(root, width=60)
command_entry.place(relx=".35",rely=".61",relwidth=".5",relheight=".05")
command_entry.bind("<Return>", lambda e: send_command())

# Load servers dynamically
servers = find_servers()
if not servers:
    messagebox.showinfo("No Servers Found", f"No server folders found in {SERVERS_DIR}.\nPlace your server folders there.")
selected_server = tk.StringVar()
selected_server.set(list(servers.keys())[0] if servers else "")

# Dropdown

menu_label = tk.Label(root, text="Select a Server")
menu_label.place(relx=".05",rely=".3",relwidth=".2",relheight=".04")
server_menu = ttk.Combobox(root, textvariable=selected_server, values=list(servers.keys()), state="readonly")
server_menu.place(relx=".05",rely=".4",relwidth=".2",relheight=".04")

# Buttons
start_btn = tk.Button(root, text="Start Server", command=start_server)
start_btn.place(relx=".35",rely=".7",relwidth=".15",relheight=".05")

stop_btn = tk.Button(root, text="Stop Server", command=stop_server, state=tk.DISABLED)
stop_btn.place(relx=".5",rely=".7",relwidth=".15",relheight=".05")

send_btn = tk.Button(root, text="Send Command", command=send_command)
send_btn.place(relx=".85",rely=".61",relwidth=".15",relheight=".05")

open_btn = tk.Button(root, text="Open Folder", command=lambda:open_folder(SERVERS_DIR))
open_btn.place(relx=".75",rely=".7",relwidth=".15",relheight=".05")

refresh_btn = tk.Button(root, text="Refresh Files", command=refresh)
refresh_btn.place(relx=".07",rely=".7",relwidth=".15",relheight=".05")

rcon_check = tk.Checkbutton(root,text="Enable RCON",variable=rcon_enabled,command=configure_rcon)
rcon_check.place(relx=-0.05, rely=0.2, relwidth=0.35, relheight=0.1)

root.mainloop()
