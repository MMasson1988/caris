# -*- coding: utf-8 -*-
import os, sys, threading, queue, logging, re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

MODULE_NAME = "commcare_downloader"
ID_ENV_FILENAME = "id_cc.env"

try:
    downloader = __import__(MODULE_NAME)
except Exception as e:
    raise SystemExit(
        f"Impossible d'importer le module '{MODULE_NAME}'. "
        f"Place ton script comme '{MODULE_NAME}.py' dans ce dossier.\nErreur: {e}"
    )

log_queue = queue.Queue()

class TkQueueHandler(logging.Handler):
    def emit(self, record):
        try: log_queue.put_nowait(record)
        except Exception: pass

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
formatter = logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S")
root_logger = logging.getLogger(); root_logger.setLevel(logging.INFO)
gui_handler = TkQueueHandler(); gui_handler.setFormatter(formatter); root_logger.addHandler(gui_handler)
for h in list(root_logger.handlers):
    if h is not gui_handler:
        root_logger.removeHandler(h)

class SmartDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 Smart CommCare Downloader - Interface Professionnelle")
        self.geometry("1400x900")
        self.minsize(1200, 800)
        self.state('zoomed')
        
        # 🎨 Configuration des couleurs et styles
        self._setup_styles()
        
        # Variables de l'application
        self.running_thread = None
        self.keep_env_file = tk.BooleanVar(value=False)
        self.headless_var = tk.BooleanVar(value=bool(getattr(downloader, "HEADLESS", False)))
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.force_download_var = tk.BooleanVar(value=False)
        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        default_dir = getattr(downloader, "DOWNLOAD_DIR", str(Path.home() / "Downloads"))
        self.dir_var = tk.StringVar(value=default_dir)
        self.base_vars = []
        
        # Configuration de l'interface
        self.configure(bg='#f0f2f5')
        self._build_ui()
        self._load_expected_bases()
        self._poll_log_queue()

    def _setup_styles(self):
        """Configure les styles TTK avec des couleurs modernes"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 🎨 Couleurs principales
        self.colors = {
            'primary': '#3498db',      # Bleu principal
            'secondary': '#2c3e50',    # Gris foncé
            'success': '#27ae60',      # Vert
            'warning': '#f39c12',      # Orange
            'danger': '#e74c3c',       # Rouge
            'info': '#17a2b8',         # Cyan
            'light': '#f8f9fa',        # Gris très clair
            'dark': '#343a40',         # Gris très foncé
            'background': '#f0f2f5',   # Fond principal
            'card': '#ffffff',         # Fond des cartes
            'border': '#dee2e6'        # Bordures
        }
        
        # 🎨 Styles pour LabelFrame (cartes)
        style.configure('Card.TLabelframe', 
                       background=self.colors['card'],
                       borderwidth=2,
                       relief='solid')
        style.configure('Card.TLabelframe.Label',
                       background=self.colors['card'],
                       foreground=self.colors['secondary'],
                       font=('Segoe UI', 10, 'bold'))
        
        # 🎨 Styles pour les boutons
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       font=('Segoe UI', 9, 'bold'),
                       padding=(20, 10))
        style.map('Primary.TButton',
                 background=[('active', '#2980b9')])
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       font=('Segoe UI', 9, 'bold'),
                       padding=(15, 8))
        style.map('Success.TButton',
                 background=[('active', '#229954')])
        
        style.configure('Warning.TButton',
                       background=self.colors['warning'],
                       foreground='white',
                       font=('Segoe UI', 9, 'bold'),
                       padding=(15, 8))
        style.map('Warning.TButton',
                 background=[('active', '#d68910')])
        
        style.configure('Danger.TButton',
                       background=self.colors['danger'],
                       foreground='white',
                       font=('Segoe UI', 9, 'bold'),
                       padding=(15, 8))
        style.map('Danger.TButton',
                 background=[('active', '#c0392b')])
        
        # 🎨 Styles pour les checkboxes
        style.configure('Modern.TCheckbutton',
                       background=self.colors['card'],
                       foreground=self.colors['secondary'],
                       font=('Segoe UI', 9))
        
        # 🎨 Styles pour les entrées
        style.configure('Modern.TEntry',
                       padding=8,
                       font=('Segoe UI', 9))

    def _build_ui(self):
        # 🌟 En-tête avec dégradé visuel
        self._create_header()
        
        # 📋 Container principal avec défilement
        main_container = self._create_scrollable_container()
        
        # 🔐 Section Identifiants
        self._create_credentials_section(main_container)
        
        # ⚙️ Section Configuration
        self._create_config_section(main_container)
        
        # 📊 Section Sélection des exports
        self._create_exports_section(main_container)
        
        # 🚀 Section Actions principales
        self._create_main_actions_section(main_container)
        
        # 🎯 Section Actions spécialisées
        self._create_specialized_actions_section(main_container)
        
        # 🛠️ Barre d'outils
        self._create_toolbar(main_container)
        
        # 📋 Zone de logs
        self._create_logs_section()
        
        # 📊 Barre de statut
        self._create_status_bar()

    def _create_header(self):
        """Crée un en-tête moderne avec dégradé"""
        header_frame = tk.Frame(self, height=80, bg='#2c3e50')
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        # Conteneur pour centrer le contenu
        content_frame = tk.Frame(header_frame, bg='#2c3e50')
        content_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Titre principal avec style
        title_label = tk.Label(content_frame, 
                              text="🚀 Smart CommCare Downloader",
                              font=('Segoe UI', 24, 'bold'),
                              fg='white',
                              bg='#2c3e50')
        title_label.pack()
        
        # Sous-titre
        subtitle_label = tk.Label(content_frame,
                                 text="Interface Professionnelle de Téléchargement Intelligent",
                                 font=('Segoe UI', 11),
                                 fg='#bdc3c7',
                                 bg='#2c3e50')
        subtitle_label.pack(pady=(5, 0))

    def _create_scrollable_container(self):
        """Crée un conteneur principal avec défilement"""
        # Canvas et scrollbar pour le défilement
        canvas = tk.Canvas(self, bg=self.colors['background'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['background'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack le canvas et scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        scrollbar.pack(side="right", fill="y")
        
        return scrollable_frame

    def _create_credentials_section(self, parent):
        """Section des identifiants avec icônes"""
        creds_frame = ttk.LabelFrame(parent, text="🔐 Identifiants CommCare", 
                                    style='Card.TLabelframe', padding=20)
        creds_frame.pack(fill="x", pady=(0, 15))
        
        # Container pour organisation en grille
        grid_frame = tk.Frame(creds_frame, bg=self.colors['card'])
        grid_frame.pack(fill="x")
        
        # Email
        email_frame = tk.Frame(grid_frame, bg=self.colors['card'])
        email_frame.grid(row=0, column=0, sticky="ew", padx=(0, 20), pady=10)
        
        tk.Label(email_frame, text="📧 Email:", 
                font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['card'], 
                fg=self.colors['secondary']).pack(anchor="w")
        
        email_entry = ttk.Entry(email_frame, textvariable=self.email_var, 
                               style='Modern.TEntry', width=40)
        email_entry.pack(fill="x", pady=(5, 0))
        
        # Mot de passe
        pass_frame = tk.Frame(grid_frame, bg=self.colors['card'])
        pass_frame.grid(row=0, column=1, sticky="ew", pady=10)
        
        tk.Label(pass_frame, text="🔒 Mot de passe:", 
                font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['card'], 
                fg=self.colors['secondary']).pack(anchor="w")
        
        pass_container = tk.Frame(pass_frame, bg=self.colors['card'])
        pass_container.pack(fill="x", pady=(5, 0))
        
        self.pwd_entry = ttk.Entry(pass_container, textvariable=self.pass_var, 
                                  style='Modern.TEntry', show="•", width=30)
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        show_btn = ttk.Checkbutton(pass_container, text="👁️ Afficher", 
                                  style='Modern.TCheckbutton',
                                  command=self._toggle_password)
        show_btn.pack(side="left")
        
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

    def _toggle_password(self):
        """Basculer l'affichage du mot de passe"""
        current = self.pwd_entry.cget("show")
        self.pwd_entry.config(show="" if current == "•" else "•")

    def _create_config_section(self, parent):
        """Section de configuration avec design moderne"""
        config_frame = ttk.LabelFrame(parent, text="⚙️ Configuration du Téléchargement", 
                                     style='Card.TLabelframe', padding=20)
        config_frame.pack(fill="x", pady=(0, 15))
        
        # Dossier de téléchargement
        dir_frame = tk.Frame(config_frame, bg=self.colors['card'])
        dir_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(dir_frame, text="📂 Dossier de téléchargement:", 
                font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['card'], 
                fg=self.colors['secondary']).pack(anchor="w")
        
        dir_container = tk.Frame(dir_frame, bg=self.colors['card'])
        dir_container.pack(fill="x", pady=(5, 0))
        
        ttk.Entry(dir_container, textvariable=self.dir_var, 
                 style='Modern.TEntry').pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ttk.Button(dir_container, text="📁 Parcourir", 
                  command=self._browse_dir,
                  style='Primary.TButton').pack(side="left")
        
        # Options de téléchargement dans une grille colorée
        options_frame = tk.Frame(config_frame, bg=self.colors['card'])
        options_frame.pack(fill="x", pady=(10, 0))
        
        # Option 1: Mode invisible
        opt1_frame = tk.Frame(options_frame, bg='#e8f4fd', relief='solid', bd=1)
        opt1_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=5, ipady=10, ipadx=15)
        
        ttk.Checkbutton(opt1_frame, text="🕶️ Mode invisible (sans fenêtre Chrome)", 
                       variable=self.headless_var,
                       style='Modern.TCheckbutton').pack(anchor="w")
        
        # Option 2: Conserver fichier
        opt2_frame = tk.Frame(options_frame, bg='#f0f8e8', relief='solid', bd=1)
        opt2_frame.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=5, ipady=10, ipadx=15)
        
        ttk.Checkbutton(opt2_frame, text="💾 Conserver id_cc.env après téléchargement", 
                       variable=self.keep_env_file,
                       style='Modern.TCheckbutton').pack(anchor="w")
        
        # Option 3: Ignorer existants
        opt3_frame = tk.Frame(options_frame, bg='#fff3e0', relief='solid', bd=1)
        opt3_frame.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5, ipady=10, ipadx=15)
        
        ttk.Checkbutton(opt3_frame, text="⏭️ Ignorer fichiers déjà téléchargés", 
                       variable=self.skip_existing_var,
                       command=self._on_skip_existing_change,
                       style='Modern.TCheckbutton').pack(anchor="w")
        
        # Option 4: Forcer téléchargement
        opt4_frame = tk.Frame(options_frame, bg='#ffebee', relief='solid', bd=1)
        opt4_frame.grid(row=1, column=1, sticky="ew", pady=5, ipady=10, ipadx=15)
        
        ttk.Checkbutton(opt4_frame, text="🔄 Forcer le téléchargement", 
                       variable=self.force_download_var,
                       command=self._on_force_download_change,
                       style='Modern.TCheckbutton').pack(anchor="w")
        
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)

    def _create_exports_section(self, parent):
        """Section de sélection des exports avec design amélioré"""
        sel_frame = ttk.LabelFrame(parent, text="📊 Sélection des Exports CommCare", 
                                  style='Card.TLabelframe', padding=20)
        sel_frame.pack(fill="both", expand=False, pady=(0, 15))
        
        # Canvas avec scrollbar stylisée
        canvas_frame = tk.Frame(sel_frame, bg=self.colors['card'])
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, height=300, bg=self.colors['light'], 
                          highlightthickness=0, relief='flat')
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        self.list_frame = tk.Frame(canvas, bg=self.colors['light'])
        self.list_frame.bind("<Configure>", 
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_main_actions_section(self, parent):
        """Section des actions principales avec boutons stylisés"""
        actions_frame = tk.Frame(parent, bg=self.colors['background'])
        actions_frame.pack(fill="x", pady=(0, 15))
        
        # Container pour centrer les boutons
        buttons_container = tk.Frame(actions_frame, bg=self.colors['background'])
        buttons_container.pack()
        
        # Bouton principal de téléchargement (extra large)
        self.run_btn = tk.Button(buttons_container, 
                                text="▶️ LANCER LE TÉLÉCHARGEMENT", 
                                command=self._on_run,
                                font=('Segoe UI', 14, 'bold'),
                                bg=self.colors['success'],
                                fg='white',
                                relief='flat',
                                padx=30, pady=15,
                                cursor='hand2')
        self.run_btn.pack(side="left", padx=(0, 15))
        
        # Bouton de vérification
        verify_btn = tk.Button(buttons_container,
                              text="🔍 VÉRIFIER FICHIERS",
                              command=self._check_existing_files,
                              font=('Segoe UI', 12, 'bold'),
                              bg=self.colors['info'],
                              fg='white',
                              relief='flat',
                              padx=20, pady=12,
                              cursor='hand2')
        verify_btn.pack(side="left")
        
        # Barre de progression stylisée
        progress_frame = tk.Frame(actions_frame, bg=self.colors['background'])
        progress_frame.pack(fill="x", pady=(15, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, 
                                       variable=self.progress_var,
                                       mode='indeterminate',
                                       length=400)
        self.progress.pack()

    def _create_specialized_actions_section(self, parent):
        """Section des actions spécialisées avec cartes colorées"""
        spec_frame = ttk.LabelFrame(parent, text="🎯 Actions Spécialisées & Dashboards", 
                                   style='Card.TLabelframe', padding=20)
        spec_frame.pack(fill="x", pady=(0, 15))
        
        # Grille d'actions spécialisées
        grid = tk.Frame(spec_frame, bg=self.colors['card'])
        grid.pack(fill="x")
        
        # Pipeline Call App (Carte bleue)
        call_card = tk.Frame(grid, bg='#e3f2fd', relief='solid', bd=2, padx=15, pady=15)
        call_card.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        
        tk.Label(call_card, text="📞 Pipeline Call App", 
                font=('Segoe UI', 12, 'bold'), 
                bg='#e3f2fd', fg='#1976d2').pack(anchor="w")
        
        date_frame = tk.Frame(call_card, bg='#e3f2fd')
        date_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(date_frame, text="Début:", bg='#e3f2fd', fg='#424242').pack(side="left")
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(date_frame, textvariable=self.start_date_var, width=12).pack(side="left", padx=(5, 15))
        
        tk.Label(date_frame, text="Fin:", bg='#e3f2fd', fg='#424242').pack(side="left")
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(date_frame, textvariable=self.end_date_var, width=12).pack(side="left", padx=5)
        
        ttk.Button(call_card, text="🚀 Exécuter", 
                  command=self._on_callapp_run,
                  style='Primary.TButton').pack(pady=(10, 0))
        
        # Dashboards (Carte verte)
        dash_card = tk.Frame(grid, bg='#e8f5e8', relief='solid', bd=2, padx=15, pady=15)
        dash_card.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
        
        tk.Label(dash_card, text="📊 Dashboards & Analytics", 
                font=('Segoe UI', 12, 'bold'), 
                bg='#e8f5e8', fg='#2e7d32').pack(anchor="w")
        
        dash_buttons = tk.Frame(dash_card, bg='#e8f5e8')
        dash_buttons.pack(fill="x", pady=(10, 0))
        
        ttk.Button(dash_buttons, text="🌐 PVVIH", 
                  command=self._open_dashboard_pvvih,
                  style='Success.TButton').pack(side="left", padx=(0, 5))
        
        ttk.Button(dash_buttons, text="📈 M&E", 
                  command=self._open_dashboard_me,
                  style='Success.TButton').pack(side="left")
        
        # Outils de développement (Carte orange)
        dev_card = tk.Frame(grid, bg='#fff3e0', relief='solid', bd=2, padx=15, pady=15)
        dev_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        tk.Label(dev_card, text="🛠️ Outils de Développement", 
                font=('Segoe UI', 12, 'bold'), 
                bg='#fff3e0', fg='#f57c00').pack(anchor="w")
        
        dev_buttons = tk.Frame(dev_card, bg='#fff3e0')
        dev_buttons.pack(fill="x", pady=(10, 0))
        
        ttk.Button(dev_buttons, text="💻 RStudio", 
                  command=self._run_rstudio,
                  style='Warning.TButton').pack(side="left", padx=(0, 10))
        
        ttk.Button(dev_buttons, text="🐍 Jupyter", 
                  command=self._run_jupyter,
                  style='Warning.TButton').pack(side="left")
        
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def _create_toolbar(self, parent):
        """Barre d'outils avec icônes colorées"""
        toolbar = tk.Frame(parent, bg='#34495e', height=60)
        toolbar.pack(fill="x", pady=(0, 15))
        toolbar.pack_propagate(False)
        
        # Container centré pour les boutons
        btn_container = tk.Frame(toolbar, bg='#34495e')
        btn_container.place(relx=0.5, rely=0.5, anchor='center')
        
        # Style des boutons de la toolbar
        toolbar_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 15,
            'pady': 8
        }
        
        # Bouton Effacer logs
        clear_btn = tk.Button(btn_container, text="🧹 Effacer Logs", 
                             command=self._clear_logs,
                             bg='#95a5a6', fg='white', **toolbar_style)
        clear_btn.pack(side="left", padx=5)
        
        # Bouton Ouvrir dossier
        folder_btn = tk.Button(btn_container, text="📂 Ouvrir Dossier", 
                              command=self._open_folder,
                              bg='#3498db', fg='white', **toolbar_style)
        folder_btn.pack(side="left", padx=5)
        
        # Bouton Actualiser
        refresh_btn = tk.Button(btn_container, text="🔄 Actualiser", 
                               command=self._refresh_exports,
                               bg='#27ae60', fg='white', **toolbar_style)
        refresh_btn.pack(side="left", padx=5)
        
        # Bouton Quitter
        quit_btn = tk.Button(btn_container, text="❌ Quitter", 
                            command=self._on_quit,
                            bg='#e74c3c', fg='white', **toolbar_style)
        quit_btn.pack(side="left", padx=(20, 0))

    def _create_logs_section(self):
        """Zone de logs avec style moderne"""
        logs_frame = ttk.LabelFrame(self, text="📋 Logs d'Exécution en Temps Réel", 
                                   style='Card.TLabelframe', padding=15)
        logs_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Container pour le texte et scrollbar
        text_container = tk.Frame(logs_frame, bg=self.colors['card'])
        text_container.pack(fill="both", expand=True)
        
        # Zone de texte avec police monospace
        self.text = tk.Text(text_container, 
                           wrap="word", 
                           font=('Consolas', 10),
                           bg='#1e1e1e',  # Thème sombre pour les logs
                           fg='#ffffff',
                           insertbackground='white',
                           selectbackground='#264f78',
                           relief='flat',
                           padx=10,
                           pady=10)
        
        # Scrollbar stylisée
        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configuration des couleurs pour les logs (thème sombre)
        self.text.tag_configure("INFO", foreground="#61dafb")      # Cyan clair
        self.text.tag_configure("WARNING", foreground="#ffc107")   # Jaune
        self.text.tag_configure("ERROR", foreground="#dc3545")     # Rouge
        self.text.tag_configure("CRITICAL", foreground="#dc3545", underline=True)
        self.text.tag_configure("SUCCESS", foreground="#28a745", font=("Consolas", 10, "bold"))
        self.text.tag_configure("SKIP", foreground="#6f42c1", font=("Consolas", 10, "italic"))

    def _create_status_bar(self):
        """Barre de statut moderne"""
        status_frame = tk.Frame(self, bg='#2c3e50', height=35)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        self.status = tk.Label(status_frame, 
                              text="🟢 Prêt — Smart Downloader initialisé", 
                              anchor="w", 
                              bg='#2c3e50',
                              fg='#ecf0f1',
                              font=('Segoe UI', 9),
                              padx=15)
        self.status.pack(fill="both", expand=True)

    # Méthodes de gestion des événements (inchangées)
    def _on_skip_existing_change(self):
        """Gère les changements d'état de 'ignorer existants'"""
        if self.skip_existing_var.get():
            self.force_download_var.set(False)
            # AJOUTÉ: Message informatif
            self._append_log("⏭️ Mode 'Ignorer existants' activé - les fichiers déjà présents seront ignorés\n", "INFO")

    def _on_force_download_change(self):
        """Gère les changements d'état de 'forcer téléchargement'"""
        if self.force_download_var.get():
            self.skip_existing_var.set(False)
            # Message d'avertissement
            self._append_log("⚠️ Mode 'Forcer téléchargement' activé\n", "WARNING")
            self._append_log("   → Les fichiers existants seront SUPPRIMÉS et re-téléchargés\n", "WARNING")
            self._append_log("   → Cette action est IRRÉVERSIBLE!\n", "WARNING")

    def _check_existing_files(self):
        """
        Vérifie les exports du jour en utilisant smart_downloader_updated.verify_existing_files()
        et inscrit un résumé dans la zone de logs.
        """
        try:
            present, manquants = downloader.verify_existing_files()
            self._append_log(
                f"✅ Vérification terminée : {present} fichiers présents, {manquants} manquants\n",
                "INFO"
            )
        except Exception as e:
            self._append_log(f"❌ Erreur lors de la vérification : {e}\n", "ERROR")


    def _find_existing_file(self, download_dir, base, target_date):
        """
        Recherche un fichier existant pour une base et une date données
        
        Args:
            download_dir (str): Dossier de téléchargement
            base (str): Nom de l'export
            target_date (str): Date au format YYYY-MM-DD
        
        Returns:
            str|None: Chemin du fichier trouvé ou None
        """
        try:
            download_path = Path(download_dir)
            if not download_path.exists():
                return None

            # Normaliser le nom de base pour la recherche
            base_normalized = self._normalize_filename(base)

            # Patterns de recherche pour différents formats de noms
            patterns_to_try = [
                # Pattern principal avec le nom exact
                f"*{base}*{target_date}*.xlsx",
                # Pattern avec normalisation: remplace espaces par _
                f"*{base.replace(' ', '_')}*{target_date}*.xlsx",
                # Pattern avec normalisation complète
                f"*{base_normalized}*{target_date}*.xlsx",
                # Pattern case insensitive avec nom exact
                f"*{base.lower()}*{target_date}*.xlsx",
                # Pattern très permissif - juste la date
                f"*{target_date}*.xlsx",
            ]

            # Essayer chaque pattern
            for i, pattern in enumerate(patterns_to_try):
                matching_files = list(download_path.glob(pattern))
                if matching_files:
                    # Vérifier chaque fichier trouvé
                    for file_path in matching_files:
                        if self._file_matches_base_and_date_flexible(file_path.name, base, target_date):
                            # SEUL LOG: Quand on trouve vraiment le fichier
                            return str(file_path)

            # Recherche manuelle dans tous les fichiers Excel
            for file_path in download_path.glob("*.xlsx"):
                if self._file_matches_base_and_date_flexible(file_path.name, base, target_date):
                    return str(file_path)

            # Aucun fichier trouvé
            return None

        except Exception as e:
            self._append_log(f"❌ Erreur lors de la recherche de fichier pour {base}: {e}\n", "ERROR")
            return None

    def _file_matches_base_and_date_flexible(self, filename, base, target_date):
        """
        Vérifie si un fichier correspond à une base et une date avec plus de flexibilité
        MAIS SANS FAUX POSITIFS
        """
        try:
            # Vérifier d'abord que la date est présente
            if target_date not in filename:
                return False
            
            # Vérifier que le fichier existe réellement
            if not filename or not filename.endswith('.xlsx'):
                return False
            
            # Normaliser les noms pour la comparaison
            filename_norm = self._normalize_filename(filename)
            base_norm = self._normalize_filename(base)
            
            # Méthode 1: Correspondance directe normalisée (la plus fiable)
            if base_norm in filename_norm:
                return True
            
            # Pour "Dépistage Nutritionnel", chercher les mots-clés spécifiques
            if "depistage_nutritionnel" in base_norm:
                required_words = ["depistage", "nutritionnel"]
                if all(word in filename_norm for word in required_words):
                    return True
            
            # Méthode 2: Correspondance par mots-clés (plus strict)
            base_words = base_norm.split('_')
            base_words = [w for w in base_words if len(w) > 3]  # CHANGÉ: mots > 3 caractères
            
            if len(base_words) >= 2:
                # Vérifier que au moins 80% des mots significatifs sont présents (PLUS STRICT)
                matches = sum(1 for word in base_words if word in filename_norm)
                match_ratio = matches / len(base_words)
                
                if match_ratio >= 0.8:  # CHANGÉ: 80% au lieu de 70%
                    return True
            
            return False
            
        except Exception as e:
            # En cas d'erreur, ne pas matcher
            return False

    def _normalize_filename(self, filename):
        """Normalise un nom de fichier pour la recherche - VERSION AMÉLIORÉE"""
        if not filename:
            return ""
        
        # Conversion en minuscules et suppression de l'extension
        normalized = filename.lower()
        if normalized.endswith('.xlsx'):
            normalized = normalized[:-5]
        
        # Remplacements spéciaux pour les cas problématiques
        special_replacements = {
            'nutriton': 'nutrition',  # Correction de la faute de frappe
            'hidden': '',  # Supprimer HIDDEN
            'créé': 'created',
            'créer': 'created',
        }
        
        for old, new in special_replacements.items():
            normalized = normalized.replace(old, new)
        
        # Remplacements pour normaliser
        replacements = {
            ' ': '_',
            '-': '_',
            '(': '',
            ')': '',
            '[': '',
            ']': '',
            '{': '',
            '}': '',
            '.': '_',
            ',': '',
            ';': '',
            ':': '',
            '/': '_',
            '\\': '_',
            "'": '',
            '"': '',
            '`': '',
            '&': 'and',
            '+': 'plus',
            '=': 'equals',
            '@': 'at',
            '#': 'hash',
            '%': 'percent',
            '*': 'star',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Supprimer les underscores multiples
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        
        # Supprimer les underscores en début et fin
        normalized = normalized.strip('_')
        
        return normalized

    def _load_expected_bases(self):
        """Charge et organise les exports disponibles par catégorie"""
        bases = list(getattr(downloader, "EXPECTED_BASES", [])) or \
                list(getattr(downloader, "EXPORT_URLS", {}).keys())
        bases = sorted(bases, key=str.lower)
        
        # NOUVEAU: Mapping des noms d'affichage simplifiés
        DISPLAY_NAMES = {
            "Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel": "Dépistage Nutritionnel",
            "Caris Health Agent - Enfant - Visite Enfant": "Visite Enfant",
            "Caris Health Agent - Enfant - APPELS OEV": "Appels OEV",
            "Caris Health Agent - Femme PMTE  - Visite PTME": "Visite PTME",
            "Caris Health Agent - Femme PMTE  - Ration & Autres Visites": "Ration PTME",
            "Caris Health Agent - Enfant - Ration et autres visites": "Ration Enfant",
            "Caris Health Agent - Femme PMTE  - APPELS PTME": "Appels PTME",
            "Ajout de menages ptme [officiel]": "Ajout de ménage PTME",
            "PTME WITH PATIENT CODE": "PTME avec Code Patient",
            "All_child_PatientCode_CaseID": "Enfants - Code Patient",
            "MUSO - Members - PPI Questionnaires": "MUSO - Questionnaires PPI",
                # Nouveaux fichiers nutrition
            "Caris Health Agent - Nutrition - Suivi nutritionel" : "Suivi Nutritionnel",
            "ht_nutrition_presence" : "Club Nutritionnelle",
            "household_nutrition" : "Ménage Nutrition",
        }
        
        # Mapping amélioré des programmes
        PROGRAM_CATEGORIES = {
            "CALL": {"icon": "📞", "color": "#3498db"},
            "PTME": {"icon": "👶", "color": "#9b59b6"},
            "OEV": {"icon": "🎒", "color": "#e74c3c"},
            "MUSO": {"icon": "🤝", "color": "#27ae60"},
            "GARDENS": {"icon": "🌱", "color": "#16a085"},
            "NUTRITION": {"icon": "🍎", "color": "#f39c12"}
        }
        
        # Classification des bases
        categorized_bases = {cat: [] for cat in PROGRAM_CATEGORIES}
        
        for b in bases:
            b_low = b.lower()
            if "appels" in b_low or "visite" in b_low or "call" in b_low:
                categorized_bases["CALL"].append(b)            
            elif "ptme" in b_low or "officiel" in b_low or "mother" in b_low:
                categorized_bases["PTME"].append(b)
            elif "child" in b_low or "caseid" in b_low or "household_child" in b_low or "oev" in b_low:
                categorized_bases["OEV"].append(b)
            elif "muso" in b_low:
                categorized_bases["MUSO"].append(b)
            elif "nutrition" in b_low or "nutriton" in b_low or "depistage" in b_low:  # AJOUTÉ: détection nutrition améliorée
                categorized_bases["NUTRITION"].append(b)
            else:
                categorized_bases["GARDENS"].append(b)
        
        # En-tête de sélection
        head = ttk.Frame(self.list_frame)
        head.pack(fill="x", pady=(0,10))
        self.select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(head, text="🔘 Tout sélectionner / désélectionner", 
                       variable=self.select_all_var, command=self._toggle_all).pack(side="left")
        ttk.Label(head, text="  —  Seuls les éléments cochés seront téléchargés", 
                 foreground="#666").pack(side="left")

        # Grille des catégories
        cats_with_content = [cat for cat in PROGRAM_CATEGORIES if categorized_bases[cat]]
        n_col = min(len(cats_with_content), 3)  # Max 3 colonnes
        
        grid_frame = ttk.Frame(self.list_frame)
        grid_frame.pack(fill="x", padx=2, pady=2)
        
        self.program_select_vars = {}
        self.program_base_vars = {cat: [] for cat in cats_with_content}
        
        def update_program_var(cat):
            """Met à jour l'état de la case programme"""
            if not self.program_base_vars[cat]:
                return
            all_checked = all(v.get() for _, v in self.program_base_vars[cat])
            all_unchecked = all(not v.get() for _, v in self.program_base_vars[cat])
            if all_checked:
                self.program_select_vars[cat].set(True)
            elif all_unchecked:
                self.program_select_vars[cat].set(False)
        
        # Création des frames par catégorie
        for idx, cat in enumerate(cats_with_content):
            row = idx // n_col
            col = idx % n_col
            
            # Frame principale pour la catégorie
            cat_info = PROGRAM_CATEGORIES[cat]
            lf = ttk.LabelFrame(grid_frame, 
                               text=f"{cat_info['icon']} {cat} ({len(categorized_bases[cat])})", 
                               padding=(8,4,8,8))
            lf.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            
            # Variable de sélection pour toute la catégorie
            prog_var = tk.BooleanVar(value=True)
            self.program_select_vars[cat] = prog_var
            
            def make_toggle(cat=cat):
                def toggle():
                    val = self.program_select_vars[cat].get()
                    for _, v in self.program_base_vars[cat]:
                        v.set(val)
                return toggle
            
            # Checkbox pour toute la catégorie
            cat_cb = ttk.Checkbutton(lf, text="Tout sélectionner/désélectionner", 
                                    variable=prog_var, command=make_toggle(cat))
            cat_cb.pack(anchor="w", pady=(0,4))
            
            # Checkboxes pour chaque export
            for b in categorized_bases[cat]:
                var = tk.BooleanVar(value=True)
                
                def make_child_callback(cat=cat, var=var):
                    def cb(*args):
                        update_program_var(cat)
                    return cb
                
                var.trace_add('write', make_child_callback(cat, var))
                
                # MODIFIÉ: Utiliser le nom d'affichage simplifié
                display_name = DISPLAY_NAMES.get(b, b)
                if len(display_name) > 40:
                    display_name = display_name[:37] + "..."
                
                cb = ttk.Checkbutton(lf, text=display_name, variable=var)
                cb.pack(anchor="w", padx=(10,0))
                
                # IMPORTANT: Garder le nom original pour le téléchargement
                self.base_vars.append((b, var))  # b = nom original complet
                self.program_base_vars[cat].append((b, var))
        
        # Configuration de la grille
        for c in range(n_col):
            grid_frame.grid_columnconfigure(c, weight=1)

    def _toggle_all(self):
        """Bascule toutes les sélections"""
        state = self.select_all_var.get()
        for _, v in self.base_vars:
            v.set(state)
        for cat_var in self.program_select_vars.values():
            cat_var.set(state)

    def _refresh_exports(self):
        """Actualise la liste des exports disponibles"""
        try:
            # Recharger le module downloader
            import importlib
            importlib.reload(downloader)
            
            # Nettoyer et recharger la liste
            for widget in self.list_frame.winfo_children():
                widget.destroy()
            
            self.base_vars.clear()
            self._load_expected_bases()
            self._append_log("✅ Liste des exports actualisée\n", "SUCCESS")
            
        except Exception as e:
            self._append_log(f"❌ Erreur lors de l'actualisation: {e}\n", "ERROR")

    def _browse_dir(self):
        """Ouvre le sélecteur de dossier"""
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()))
        if d:
            self.dir_var.set(d)

    def _open_folder(self):
        """Ouvre le dossier de téléchargement"""
        path = self.dir_var.get()
        p = Path(path)
        if not p.exists():
            messagebox.showerror("Erreur", f"Dossier introuvable: {p}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(p))
            elif sys.platform == "darwin":
                os.system(f"open '{p}'")
            else:
                os.system(f"xdg-open '{p}'")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {e}")

    def _clear_logs(self):
        """Efface les logs"""
        self.text.delete("1.0", "end")
        self._append_log("📋 Logs effacés\n", "INFO")

    def _append_log(self, text, level="INFO"):
        """Ajoute un message aux logs"""
        self.text.insert("end", text, level)
        self.text.see("end")

    def _poll_log_queue(self):
        """Récupère les messages de log du thread de téléchargement"""
        import queue as q
        try:
            while True:
                record = log_queue.get_nowait()
                msg = formatter.format(record) + "\n"
                level = record.levelname if record.levelname in ("INFO","WARNING","ERROR","CRITICAL") else "INFO"
                self._append_log(msg, level)
                self.status.config(text=f"📡 {record.levelname}: {record.getMessage()[:50]}...")
        except q.Empty:
            pass
        self.after(120, self._poll_log_queue)

    def _on_run(self):
        """Lance le téléchargement principal avec filtrage intelligent"""
        if self.running_thread and self.running_thread.is_alive():
            messagebox.showinfo("En cours", "Un téléchargement est déjà en cours.")
            return
            
        selected = [b for (b,v) in self.base_vars if v.get()]
        if not selected:
            messagebox.showwarning("Sélection vide", "Veuillez cocher au moins un export à télécharger.")
            return
            
        dl_dir = self.dir_var.get().strip()
        if not dl_dir:
            messagebox.showwarning("Dossier manquant", "Veuillez choisir un dossier de téléchargement.")
            return
            
        Path(dl_dir).mkdir(parents=True, exist_ok=True)

        # Gérer les différents modes correctement
        self._append_log(f"\n{'='*60}\n🚀 PRÉPARATION DU TÉLÉCHARGEMENT\n{'='*60}\n", "INFO")
        self._append_log(f"📊 Exports sélectionnés: {len(selected)}\n", "INFO")
        
        # Vérifier les options de téléchargement
        force_mode = self.force_download_var.get()
        skip_mode = self.skip_existing_var.get()
        
        # NOUVEAU: Confirmation pour le mode force
        if force_mode:
            # Compter les fichiers qui seront supprimés
            files_to_delete = []
            today = datetime.now().strftime('%Y-%m-%d')
            for base in selected:
                existing_file = self._find_existing_file(dl_dir, base, today)
                if existing_file:
                    files_to_delete.append(Path(existing_file).name)
            
            if files_to_delete:
                msg = f"⚠️ MODE FORCE TÉLÉCHARGEMENT ⚠️\n\n"
                msg += f"Cette opération va SUPPRIMER {len(files_to_delete)} fichier(s) existant(s)\n"
                msg += f"et les re-télécharger.\n\n"
                msg += f"Fichiers qui seront supprimés :\n"
                for fname in files_to_delete[:5]:  # Montrer les 5 premiers
                    msg += f"• {fname}\n"
                if len(files_to_delete) > 5:
                    msg += f"... et {len(files_to_delete) - 5} autres\n"
                msg += f"\n⚠️ Cette action est IRRÉVERSIBLE !\n\n"
                msg += f"Continuer ?"
                
                if not messagebox.askyesno("⚠️ Confirmation Force Téléchargement", msg, icon="warning"):
                    self._append_log("❌ ANNULÉ PAR L'UTILISATEUR\n", "WARNING")
                    return
        
        if force_mode:
            self._append_log("🔄 MODE FORCE TÉLÉCHARGEMENT ACTIVÉ\n", "WARNING")
            self._append_log("   → Suppression et re-téléchargement de tous les fichiers\n", "WARNING")
            exports_to_download, skipped_exports = self._filter_exports_to_download(selected)
        elif skip_mode:
            self._append_log("⏭️ MODE IGNORER EXISTANTS ACTIVÉ\n", "INFO")
            self._append_log("   → Vérification des fichiers déjà présents...\n", "INFO")
            exports_to_download, skipped_exports = self._filter_exports_to_download(selected)
        else:
            self._append_log("📥 MODE TÉLÉCHARGEMENT NORMAL\n", "INFO")
            self._append_log("   → Tous les fichiers seront téléchargés sans vérification\n", "INFO")
            exports_to_download = selected
            skipped_exports = []

        # Afficher le résumé du filtrage
        if skipped_exports:
            self._append_log(f"\n📋 RÉSUMÉ DU FILTRAGE:\n", "INFO")
            self._append_log(f"   📊 Sélectionnés: {len(selected)}\n", "INFO")
            self._append_log(f"   ⏭️ Ignorés (déjà présents): {len(skipped_exports)}\n", "SKIP")
            self._append_log(f"   ⬇️ À télécharger: {len(exports_to_download)}\n", "SUCCESS")
            
            if not exports_to_download:
                self._append_log("\n🎉 AUCUN TÉLÉCHARGEMENT NÉCESSAIRE\n", "SUCCESS")
                self._append_log("Tous les fichiers sélectionnés existent déjà pour aujourd'hui.\n\n", "SUCCESS")
                self._append_log("Options pour forcer le téléchargement:\n", "INFO")
                self._append_log("• Cochez 'Forcer le téléchargement'\n", "INFO")
                self._append_log("• Ou décochez 'Ignorer les fichiers existants'\n", "INFO")
                
                messagebox.showinfo("Rien à télécharger", 
                                  f"Tous les fichiers sélectionnés ({len(selected)}) existent déjà pour aujourd'hui.\n\n"
                                  f"Pour forcer le téléchargement :\n"
                                  f"• Cochez 'Forcer le téléchargement'\n"
                                  f"• Ou décochez 'Ignorer les fichiers existants'")
                return
        else:
            # Aucun fichier ignoré
            if force_mode:
                self._append_log(f"\n🔄 MODE FORCE: Tous les {len(exports_to_download)} fichiers seront re-téléchargés\n", "WARNING")
            else:
                self._append_log(f"\n📥 TÉLÉCHARGEMENT: {len(exports_to_download)} fichiers\n", "SUCCESS")

        # Lister les fichiers à télécharger
        self._append_log("\n📥 FICHIERS À TÉLÉCHARGER:\n", "INFO")
        for i, export in enumerate(exports_to_download, 1):
            self._append_log(f"  {i:2d}. {export}\n", "INFO")
        
        # Configuration du downloader
        downloader.DOWNLOAD_DIR = dl_dir
        downloader.HEADLESS = bool(self.headless_var.get())
        downloader.EXPECTED_BASES = exports_to_download  # Liste filtrée
        
        email = self.email_var.get().strip()
        password = self.pass_var.get().strip()
        
        if not email or not password:
            if not messagebox.askyesno("Sans identifiants",
                                     "EMAIL/PASSWORD non renseignés.\n"
                                     "Le script essaiera d'utiliser un fichier id_cc.env existant.\n"
                                     "Continuer ?"):
                return
        
        def write_env():
            if not email or not password:
                return None
            env_content = f"EMAIL={email}\nPASSWORD={password}\n"
            Path(ID_ENV_FILENAME).write_text(env_content, encoding="utf-8")
            return Path(ID_ENV_FILENAME)
        
        env_path = write_env()
        self.run_btn.config(state="disabled")
        self.progress.start()
        
        # Message de statut selon le mode
        if force_mode:
            self.status.config(text="🔄 Suppression et re-téléchargement forcé en cours...")
            self._append_log(f"\n🔄 LANCEMENT DU RE-TÉLÉCHARGEMENT FORCÉ\n", "WARNING")
        else:
            self.status.config(text="🚀 Téléchargement en cours...")
            self._append_log(f"\n🚀 LANCEMENT DU TÉLÉCHARGEMENT\n", "SUCCESS")
    
        def worker():
            try:
                # Appel de la fonction principale
                if hasattr(downloader, 'main_enhanced'):
                    downloader.main_enhanced()
                elif hasattr(downloader, 'main'):
                    downloader.main()
                else:
                    raise Exception("Aucune fonction main trouvée dans smart_downloader")
                    
                self.after(0, lambda: self._append_log("\n✅ TÉLÉCHARGEMENT TERMINÉ AVEC SUCCÈS!\n", "SUCCESS"))
                
            except Exception as e:
                logging.getLogger().exception(f"Erreur pendant l'exécution: {e}")
                self.after(0, lambda: self._append_log(f"\n❌ ERREUR: {e}\n", "ERROR"))
            finally:
                # Nettoyage
                if env_path and not self.keep_env_file.get():
                    try:
                        Path(env_path).unlink(missing_ok=True)
                        logging.getLogger().info("Fichier id_cc.env temporaire supprimé.")
                    except Exception:
                        pass
            
                self.after(0, lambda: self.run_btn.config(state="normal"))
                self.after(0, lambda: self.progress.stop())
                self.after(0, lambda: self.status.config(text="✅ Téléchargement terminé"))
        
        self.running_thread = threading.Thread(target=worker, daemon=True)
        self.running_thread.start()

    def _on_callapp_run(self):
        """Lance le pipeline Call App"""
        try:
            import subprocess
            subprocess.Popen([sys.executable, "call_pipeline.py"], cwd=os.getcwd())
            self._append_log("🚀 Pipeline Call App lancé\n", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'exécuter call_pipeline.py : {e}")
            self._append_log(f"❌ Erreur Call Pipeline: {e}\n", "ERROR")

    def _open_dashboard_pvvih(self):
        """Ouvre le dashboard PVVIH"""
        import webbrowser
        webbrowser.open_new("https://massonmoise.shinyapps.io/dashboard-pvvih/")
        self._append_log("🌐 Dashboard PVVIH ouvert dans le navigateur\n", "INFO")

    def _open_dashboard_me(self):
        """Ouvre le dashboard M&E local"""
        try:
            import webbrowser
            dashboard_path = Path("index.html")
            if dashboard_path.exists():
                webbrowser.open_new(f"file://{dashboard_path.absolute()}")
                self._append_log("📈 Dashboard M&E ouvert\n", "INFO")
            else:
                messagebox.showwarning("Dashboard introuvable", 
                                     "Le fichier index.html du dashboard M&E n'existe pas.\n"
                                     "Générez-le d'abord avec Quarto.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dashboard M&E : {e}")

    def _run_rstudio(self):
        """Lance RStudio"""
        try:
            import subprocess
            if Path("lancer_rstudio.py").exists():
                subprocess.Popen([sys.executable, "lancer_rstudio.py"], cwd=os.getcwd())
                self._append_log("💻 RStudio lancé\n", "SUCCESS")
            else:
                messagebox.showwarning("Script manquant", "Le fichier lancer_rstudio.py n'existe pas.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer RStudio : {e}")

    def _run_jupyter(self):
        """Lance Jupyter Notebook"""
        try:
            import subprocess
            subprocess.Popen([sys.executable, "-m", "jupyter", "notebook"], cwd=os.getcwd())
            self._append_log("🐍 Jupyter Notebook lancé\n", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer Jupyter : {e}")

    def _on_quit(self):
        """Quitte l'application"""
        if self.running_thread and self.running_thread.is_alive():
            if not messagebox.askyesno("Quitter ?", 
                                     "Un téléchargement est en cours.\n"
                                     "Quitter quand même ?"):
                return
        self.destroy()

    def _delete_existing_files(self, selected_bases):
        """
        Supprime les fichiers existants pour forcer le re-téléchargement
        
        Args:
            selected_bases (list): Liste des exports sélectionnés
            
        Returns:
            int: Nombre de fichiers supprimés
        """
        dl_dir = self.dir_var.get().strip()
        today = datetime.now().strftime('%Y-%m-%d')
        deleted_count = 0
        
        self._append_log("🗑️ SUPPRESSION DES FICHIERS EXISTANTS POUR FORCER LE RE-TÉLÉCHARGEMENT\n", "WARNING")
        self._append_log(f"📁 Dossier: {dl_dir}\n", "INFO")
        self._append_log(f"📅 Date ciblée: {today}\n", "INFO")
        
        for base in selected_bases:
            existing_file = self._find_existing_file(dl_dir, base, today)
            if existing_file:
                try:
                    file_path = Path(existing_file)
                    if file_path.exists():
                        # Vérifier que c'est bien un fichier Excel d'aujourd'hui
                        if file_path.suffix.lower() == '.xlsx' and today in file_path.name:
                            file_size = file_path.stat().st_size
                            file_size_mb = file_size / (1024 * 1024)
                            
                            # Supprimer le fichier
                            file_path.unlink()
                            deleted_count += 1
                            
                            self._append_log(f"🗑️ SUPPRIMÉ: {file_path.name} ({file_size_mb:.1f} MB)\n", "WARNING")
                        else:
                            self._append_log(f"⚠️ IGNORÉ: {file_path.name} (pas un fichier Excel d'aujourd'hui)\n", "WARNING")
                    else:
                        self._append_log(f"❓ INTROUVABLE: {existing_file}\n", "WARNING")
                        
                except Exception as e:
                    self._append_log(f"❌ ERREUR lors de la suppression de {existing_file}: {e}\n", "ERROR")
            else:
                self._append_log(f"✅ AUCUN FICHIER À SUPPRIMER POUR: {base}\n", "INFO")
        
        if deleted_count > 0:
            self._append_log(f"\n🗑️ RÉSUMÉ SUPPRESSION: {deleted_count} fichier(s) supprimé(s)\n", "WARNING")
        else:
            self._append_log(f"\n✅ AUCUN FICHIER À SUPPRIMER TROUVÉ\n", "INFO")
            
        return deleted_count

    def _filter_exports_to_download(self, selected_bases):
        """
        Filtre les exports à télécharger selon les options choisies
        
        Args:
            selected_bases (list): Liste des exports sélectionnés
        
        Returns:
            tuple: (exports_to_download, skipped_exports)
        """
        # CORRIGÉ: Vérifier d'abord le mode force
        if self.force_download_var.get():
            # Mode force: supprimer les fichiers existants puis télécharger TOUT
            self._append_log("🔄 MODE FORCE ACTIVÉ - Suppression et re-téléchargement de tous les fichiers\n", "WARNING")
            
            # Supprimer les fichiers existants
            deleted_count = self._delete_existing_files(selected_bases)
            
            if deleted_count > 0:
                self._append_log(f"✅ Prêt pour le re-téléchargement de {len(selected_bases)} fichiers\n", "SUCCESS")
            else:
                self._append_log(f"📥 Aucun fichier existant trouvé - téléchargement normal de {len(selected_bases)} fichiers\n", "INFO")
                
            return selected_bases, []

        if not self.skip_existing_var.get():
            # Mode normal: télécharger tout sans vérifier l'existence
            return selected_bases, []

        # Mode skip: filtrer les existants
        dl_dir = self.dir_var.get().strip()
        today = datetime.now().strftime('%Y-%m-%d')
        
        to_download = []
        skipped = []

        self._append_log("🔍 Vérification des fichiers existants...\n", "INFO")
        
        for base in selected_bases:
            existing_file = self._find_existing_file(dl_dir, base, today)
            if existing_file:
                skipped.append((base, existing_file))
                self._append_log(f"⏭️ IGNORÉ: {base} (fichier existant trouvé)\n", "SKIP")
            else:
                to_download.append(base)
                self._append_log(f"📥 À TÉLÉCHARGER: {base}\n", "INFO")

        return to_download, skipped

def file_matches_today(base, fname):
    """Vérifie si un fichier correspond au pattern d'aujourd'hui"""
    today = datetime.today().strftime('%Y-%m-%d')
    
    # Utilisation de la fonction du downloader si disponible
    if hasattr(downloader, 'build_pattern_with_today'):
        pattern = downloader.build_pattern_with_today(base)
        return bool(pattern.match(os.path.basename(fname)))
    
    # Fallback vers l'ancienne logique
    base_norm = base.lower().replace(" ", "_")
    fname_norm = os.path.basename(fname).lower().replace(" ", "_")
    pat = re.compile(rf"^{re.escape(base_norm)}(\s*\(created\s+\d{{4}}-\d{{2}}-\d{{2}}\))?\s+{today}(?:\s+\(\d+\))?\.xlsx$")
    return bool(pat.match(fname_norm))

if __name__ == "__main__":
    try:
        app = SmartDownloaderApp()
        app.mainloop()
    except Exception as e:
        print(f"Erreur fatale : {e}")
        messagebox.showerror("Erreur", f"Impossible de lancer l'application : {e}")