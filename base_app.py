# base_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import matplotlib.pyplot as plt

class BaseApp(ttk.Frame):
    def __init__(self, parent, app_name="Analyzer", version="1.0", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.app_name = app_name
        self.version = version
        self.parent.title(f"{app_name} v{version} - © 2025 Patrick Oppermann")
        self.parent.state('zoomed')
        self._setup_menu()
        self.after(100, lambda: sv_ttk.set_theme("light"))

    def _setup_menu(self):
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Heller Modus", command=lambda: self._set_theme("light"))
        view_menu.add_command(label="Dunkler Modus", command=lambda: self._set_theme("dark"))
        menubar.add_cascade(label="Ansicht", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=f"Über {self.app_name}", command=self._show_about_dialog)
        menubar.add_cascade(label="Hilfe", menu=help_menu)

    def _set_theme(self, theme):
        sv_ttk.set_theme(theme)
        plt.style.use('dark_background' if theme == "dark" else 'default')

    def _show_about_dialog(self):
        messagebox.showinfo(
            f"Über {self.app_name}",
            f"{self.app_name} v{self.version}\n\nCopyright © 2025, Patrick Oppermann"
        )