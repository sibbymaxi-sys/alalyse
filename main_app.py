# main_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import os
import sv_ttk
from gateview_app import GateViewApp
from mv3d_app import MV3DApp
from license_manager import validate_key

CONFIG_FILE = 'config.ini'

def get_license_info():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        user = config.get('License', 'User', fallback=None)
        key = config.get('License', 'Key', fallback=None)
        return user, key
    return None, None

def save_license_info(user, key):
    config = configparser.ConfigParser()
    config['License'] = {'User': user, 'Key': key}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

class LicenseDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Lizenzaktivierung")
        self.geometry("400x200")
        
        self.parent = parent
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.result = False

        self.update_idletasks()
        x = (self.parent.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.parent.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f'+{x}+{y}')
        self.grab_set()

        ttk.Label(self, text="Bitte geben Sie Ihre Lizenzinformationen ein:").pack(pady=10)
        frame = ttk.Frame(self, padding=10); frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Benutzername:").grid(row=0, column=0, sticky="w", pady=5)
        self.user_entry = ttk.Entry(frame, width=40); self.user_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="Lizenzschlüssel:").grid(row=1, column=0, sticky="w", pady=5)
        self.key_entry = ttk.Entry(frame, width=40); self.key_entry.grid(row=1, column=1, sticky="ew")
        frame.columnconfigure(1, weight=1)
        ttk.Button(self, text="Aktivieren", command=self.activate).pack(pady=15)
    
    def cancel(self):
        self.result = False
        self.destroy()

    def activate(self):
        user = self.user_entry.get(); key = self.key_entry.get()
        if not user or not key:
            messagebox.showerror("Fehler", "Bitte beide Felder ausfüllen.", parent=self); return
        is_valid, message = validate_key(user, key)
        if is_valid:
            save_license_info(user, key)
            messagebox.showinfo("Erfolg", "Lizenz erfolgreich aktiviert.\n" + message, parent=self)
            self.result = True
            self.destroy()
        else:
            messagebox.showerror("Aktivierung fehlgeschlagen", message, parent=self)

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Log Analyzer (Lizenz erforderlich)")
        self.geometry("400x250")
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f'+{x}+{y}')
        sv_ttk.set_theme("dark")
        
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Bitte wählen Sie ein Analyse-Modul:", font=("Helvetica", 14)).pack(pady=10)
        
        self.gateview_button = ttk.Button(main_frame, text="GateView Analyzer öffnen", command=self.open_gateview, state="disabled")
        self.gateview_button.pack(pady=10, fill=tk.X)
        self.mv3d_button = ttk.Button(main_frame, text="MV3D Analyzer öffnen", command=self.open_mv3d, state="disabled")
        self.mv3d_button.pack(pady=10, fill=tk.X)
        
        # Starte die Lizenzprüfung kurz nach dem das Fenster gezeichnet wurde
        self.after(100, self.check_license)
        
    def check_license(self):
        user, key = get_license_info()
        is_valid, message = (False, "")
        if user and key:
            is_valid, message = validate_key(user, key)
        
        if is_valid:
            self.title(f"Universal Log Analyzer - Lizenz: {message}")
            self.gateview_button.config(state="normal")
            self.mv3d_button.config(state="normal")
        else:
            dialog = LicenseDialog(self)
            self.wait_window(dialog)
            
            # Prüfe erneut nach der Eingabe
            if dialog.result:
                user, key = get_license_info()
                is_valid, message = validate_key(user, key)
                self.title(f"Universal Log Analyzer - Lizenz: {message}")
                self.gateview_button.config(state="normal")
                self.mv3d_button.config(state="normal")
            else:
                self.destroy()

    def open_gateview(self):
        win = tk.Toplevel(self); app = GateViewApp(win); app.pack(fill="both", expand=True)
        self.iconify()
        
    def open_mv3d(self):
        win = tk.Toplevel(self); app = MV3DApp(win); app.pack(fill="both", expand=True)
        self.iconify()

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()