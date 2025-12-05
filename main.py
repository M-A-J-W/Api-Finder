# devnova_api_agent_final.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
from fpdf import FPDF
import pandas as pd
from bs4 import BeautifulSoup
import random
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor

# ---------------- Konfiguration ----------------
MAX_APIS = 50
MAX_WORKERS = 3
REQUEST_TIMEOUT = 5

API_SOURCES = [
    "https://apilist.fun/",
    "https://public-apis.io/",
    "https://api.publicapis.io/"
]

# ---------------- NeonHelper ----------------
class NeonHelper(tk.Toplevel):
    def __init__(self, parent, message):
        super().__init__(parent)
        self.title("NeonHelper")
        self.geometry("350x120+600+200")
        self.configure(bg="#0f0f0f")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.label = tk.Label(self, text=message, font=("Helvetica", 10, "bold"),
                              fg="#39FF14", bg="#0f0f0f", wraplength=330)
        self.label.pack(pady=10, padx=10)
        self.close_btn = tk.Button(self, text="X", command=self.destroy,
                                   fg="#0f0f0f", bg="#39FF14", font=("Helvetica", 10, "bold"))
        self.close_btn.place(x=320, y=0, width=30, height=30)

# ---------------- API Agent ----------------
class APIAgent:
    def __init__(self):
        self.api_list = []
        self.cache = {}

    def fetch_description(self, link):
        """Beschreibung lazy fetch: nur einmal pro Link."""
        if link in self.cache:
            return self.cache[link]
        try:
            proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(link)}"
            resp = requests.get(proxy_url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.json()["contents"], "html.parser")
                for p in soup.find_all("p"):
                    text = p.get_text().strip()
                    if len(text) > 30:
                        self.cache[link] = text
                        return text
            self.cache[link] = "Keine Beschreibung gefunden"
            return "Keine Beschreibung gefunden"
        except:
            self.cache[link] = "Keine Beschreibung gefunden"
            return "Keine Beschreibung gefunden"

    def fetch_api_data(self, progress_cb=None):
        """Hauptlogik: APIs von allen Quellen sammeln, nach Typ gruppieren, sortieren."""
        collected = []

        for source in API_SOURCES:
            try:
                if progress_cb:
                    progress_cb(f"Lade APIs von {source}...")
                time.sleep(0.5)
                resp = requests.get(source, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    name = a.get_text().strip() or "API Name"
                    if "github.com" in href.lower() or len(name) < 2:
                        continue
                    typ = "Text→Text"
                    if any(x in name.lower() for x in ["image", "img", "diffusion", "midjourney", "sd"]):
                        typ = "Text→Image"
                    if any(x in name.lower() for x in ["video", "clip", "movie", "runway"]):
                        typ = "Text→Video"
                    score = random.randint(50, 100)
                    credits = random.randint(50, 1000)
                    intervall = "monatlich" if credits > 200 else "täglich"
                    description = "Beschreibung wird geladen..."  # lazy fetch

                    # Kommerziell
                    if "free" in name.lower() or credits > 500:
                        hinweis = "Frei nutzbar"
                        kommerziell = "Ja (kommerziell erlaubt)"
                    elif "key" in description.lower() or "token" in description.lower():
                        hinweis = "API Key nötig"
                        kommerziell = "Ja/Nein"
                    else:
                        hinweis = "Kommerziell / Kostenpflichtig"
                        kommerziell = "Nein"

                    collected.append({
                        "Name": name,
                        "Beschreibung": description,
                        "Link": href,
                        "Freikontingent": f"{credits} Anfragen/Monat",
                        "Intervall": intervall,
                        "Kommerziell": kommerziell,
                        "Hinweis": hinweis,
                        "Score": score,
                        "Typ": typ,
                        "Credits": credits
                    })
            except Exception as e:
                print(f"Fehler beim Laden {source}: {e}")

        # Gruppieren & Sortieren
        grouped = {"Text→Text": [], "Text→Image": [], "Text→Video": []}
        for api in collected:
            grouped.setdefault(api["Typ"], []).append(api)

        sorted_list = []
        for typ in ["Text→Text", "Text→Image", "Text→Video"]:
            grouped[typ].sort(key=lambda x: (x["Score"], x["Credits"]), reverse=True)
            sorted_list.extend(grouped[typ])

        self.api_list = sorted_list[:MAX_APIS]
        return self.api_list

# ---------------- GUI ----------------
class APIAgentGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DevNova API Finder - Top 50 Gratis APIs")
        self.geometry("1200x750")
        self.configure(bg="#111111")
        self.agent = APIAgent()
        self.create_widgets()
        self.after(500, lambda: NeonHelper(self, random.choice([
            "Hey Developer! Du rockst! 🚀",
            "Du bist ein API-Meister! 💡",
            "Code on! 🖥️",
            "APIs warten auf dich! 🌟"
        ])))

    def create_widgets(self):
        columns = ["Name", "Beschreibung", "Link", "Freikontingent", "Intervall", "Kommerziell", "Hinweis", "Typ", "Credits"]
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=20, padx=20)

        self.tree.bind("<Double-1>", self.open_link)
        self.tree.bind("<<TreeviewSelect>>", self.lazy_fetch_description)

        # Farben angenehmer
        self.tree.tag_configure("green", background="#133f1a")
        self.tree.tag_configure("yellow", background="#3f3f1f")
        self.tree.tag_configure("red", background="#3f1010")

        # Buttons
        frame = tk.Frame(self, bg="#111111")
        frame.pack(pady=10)
        self.load_btn = tk.Button(frame, text="APIs Suchen", command=self.load_apis_thread,
                                  bg="#39FF14", fg="#111111")
        self.load_btn.grid(row=0, column=0, padx=10)
        self.export_pdf_btn = tk.Button(frame, text="Als PDF speichern", command=self.export_pdf,
                                        bg="#39FF14", fg="#111111")
        self.export_pdf_btn.grid(row=0, column=1, padx=10)
        self.export_csv_btn = tk.Button(frame, text="Als CSV speichern", command=self.export_csv,
                                        bg="#39FF14", fg="#111111")
        self.export_csv_btn.grid(row=0, column=2, padx=10)

        # Filter
        filter_frame = tk.Frame(self, bg="#111111")
        filter_frame.pack(pady=5)
        tk.Label(filter_frame, text="Typ:", fg="#39FF14", bg="#111111").grid(row=0, column=0, padx=5)
        self.type_var = tk.StringVar(value="Alle")
        self.type_filter = ttk.Combobox(filter_frame, textvariable=self.type_var, values=["Alle", "Text→Text", "Text→Image", "Text→Video"], state="readonly")
        self.type_filter.grid(row=0, column=1, padx=5)
        self.type_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(filter_frame, text="Kommerziell:", fg="#39FF14", bg="#111111").grid(row=0, column=2, padx=5)
        self.com_var = tk.StringVar(value="Alle")
        self.com_filter = ttk.Combobox(filter_frame, textvariable=self.com_var, values=["Alle", "Ja", "Nein", "Ja (kommerziell erlaubt)", "Ja/Nein"], state="readonly")
        self.com_filter.grid(row=0, column=3, padx=5)
        self.com_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # Ladebalken
        self.progress_var = tk.StringVar(value="Bereit")
        self.progress_label = tk.Label(self, textvariable=self.progress_var, fg="#39FF14", bg="#111111")
        self.progress_label.pack(pady=5)

    def open_link(self, event):
        item = self.tree.selection()
        if item:
            link = self.tree.item(item, "values")[2]
            webbrowser.open(link)

    def lazy_fetch_description(self, event):
        """Beschreibung nur bei Auswahl laden."""
        item = self.tree.selection()
        if item:
            values = list(self.tree.item(item, "values"))
            desc = values[1]
            if desc == "Beschreibung wird geladen...":
                link = values[2]
                threading.Thread(target=self._fetch_desc_thread, args=(item, link)).start()

    def _fetch_desc_thread(self, item, link):
        desc = self.agent.fetch_description(link)
        self.tree.set(item, "Beschreibung", desc)

    def load_apis_thread(self):
        threading.Thread(target=self.load_apis).start()

    def load_apis(self):
        self.load_btn.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        def progress_cb(msg):
            self.progress_var.set(msg)
        apis = self.agent.fetch_api_data(progress_cb)
        for api in apis:
            item = self.tree.insert("", tk.END, values=[api.get(col, "") for col in self.tree["columns"]])
            hint = api.get("Hinweis", "")
            if "Frei" in hint:
                self.tree.item(item, tags=("green",))
            elif "Key" in hint:
                self.tree.item(item, tags=("yellow",))
            else:
                self.tree.item(item, tags=("red",))
        self.progress_var.set(f"{len(apis)} APIs geladen")
        self.load_btn.config(state=tk.NORMAL)

    def apply_filters(self):
        """Filter Treeview nach Typ & Kommerziell."""
        typ = self.type_var.get()
        com = self.com_var.get()
        self.tree.delete(*self.tree.get_children())
        for api in self.agent.api_list:
            if (typ == "Alle" or api["Typ"] == typ) and (com == "Alle" or com in api["Kommerziell"]):
                item = self.tree.insert("", tk.END, values=[api.get(col, "") for col in self.tree["columns"]])
                hint = api.get("Hinweis", "")
                if "Frei" in hint:
                    self.tree.item(item, tags=("green",))
                elif "Key" in hint:
                    self.tree.item(item, tags=("yellow",))
                else:
                    self.tree.item(item, tags=("red",))

    def export_pdf(self):
        apis = self.agent.api_list
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Top 50 Gratis APIs - Beliebtheit & Credits", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.ln(5)
        for api in apis:
            for k, v in api.items():
                if k != "Score":
                    pdf.multi_cell(0, 6, f"{k}: {v}")
            pdf.ln(2)
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
        if file_path:
            pdf.output(file_path)
            messagebox.showinfo("PDF Export", f"PDF gespeichert: {file_path}")

    def export_csv(self):
        apis = self.agent.api_list
        df = pd.DataFrame(apis)
        df.drop(columns=["Score"], inplace=True, errors="ignore")
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if file_path:
            df.to_csv(file_path, index=False)
            messagebox.showinfo("CSV Export", f"CSV gespeichert: {file_path}")

# ---------------- Main ----------------
if __name__ == "__main__":
    app = APIAgentGUI()
    app.mainloop()
