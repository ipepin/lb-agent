from __future__ import annotations

from datetime import datetime
import json
import os
from threading import Thread
from tkinter import END, LEFT, VERTICAL, StringVar, Text, Tk
from tkinter import messagebox, simpledialog, ttk

from app.config import AppConfig, load_config
from app.db import crud
from app.db.database import initialize_database
from app.db.models import (
    ApprovalItemModel,
    EmailModel,
    InvoiceModel,
    ProjectModel,
    ReminderModel,
    TaskModel,
)
from app.services.agent_service import AgentService
from app.services.approval_service import ApprovalService
from app.services.calendar_service import CalendarService
from app.services.classifier_service import ClassifierService
from app.services.invoice_service import InvoiceService
from app.services.parser_service import ParserService
from app.services.project_service import ProjectService
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.schemas.entities import Email, EmailClassification
from app.utils.text_utils import cleanup_email_text, html_to_text


class DesktopApp:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        initialize_database(self.config)

        self.agent_service = AgentService(self.config)
        self.approval_service = ApprovalService(self.config)
        self.calendar_service = CalendarService(self.config)
        self.classifier_service = ClassifierService()
        self.invoice_service = InvoiceService(self.config)
        self.parser_service = ParserService()
        self.project_service = ProjectService(self.config)
        self.task_service = TaskService(self.config)
        self.reminder_service = ReminderService(self.config)

        self.root = Tk()
        self.root.title("Lokální asistent")
        self.root.geometry("1280x820")
        self.root.minsize(1000, 700)
        self._configure_styles()

        self.status_var = StringVar(value="Připraveno")
        self.summary_var = StringVar(value="")
        self.email_filter_var = StringVar(value="K reseni")
        self.project_status_var = StringVar(value="Nova")
        self.sync_progress_var = StringVar(value="")

        self.email_items: list[EmailModel] = []
        self.approval_items: list[ApprovalItemModel] = []
        self.invoice_items: list[InvoiceModel] = []
        self.project_items: list[ProjectModel] = []
        self.task_items: list[TaskModel] = []
        self.reminder_items: list[ReminderModel] = []
        self.selected_email_id: str | None = None
        self.selected_approval_id: int | None = None
        self.selected_invoice_id: int | None = None
        self.selected_project_id: int | None = None
        self.selected_project_email_id: str | None = None
        self.selected_task_id: int | None = None
        self.selected_reminder_id: int | None = None
        self.selected_today_item: str | None = None
        self.selected_archive_item: str | None = None
        self.current_source_email_id: str | None = None

        self._build_ui()
        self.refresh_all()

    def run(self) -> None:
        self.root.mainloop()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        bg_color = "#f3f6fb"
        panel_color = "#ffffff"
        accent_color = "#2563eb"
        border_color = "#d9e1ee"

        self.root.configure(bg=bg_color)

        style.configure(".", background=bg_color, foreground="#18212f", font=("Segoe UI", 10))
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground="#18212f")
        style.configure(
            "Hero.TLabel",
            background=bg_color,
            foreground="#0f172a",
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "HeroSub.TLabel",
            background=bg_color,
            foreground="#5b6473",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Card.TLabelframe",
            background=panel_color,
            bordercolor=border_color,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=panel_color,
            foreground="#18212f",
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Primary.TButton",
            background=accent_color,
            foreground="#ffffff",
            padding=(14, 8),
            relief="flat",
        )
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])
        style.configure(
            "Secondary.TButton",
            background=panel_color,
            foreground="#18212f",
            padding=(12, 8),
            relief="flat",
        )
        style.map("Secondary.TButton", background=[("active", "#eff4ff")])
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(16, 10),
            font=("Segoe UI Semibold", 10),
            background="#e8eef8",
        )
        style.map("TNotebook.Tab", background=[("selected", panel_color)])
        style.configure(
            "Treeview",
            background=panel_color,
            fieldbackground=panel_color,
            rowheight=28,
            bordercolor=border_color,
        )
        style.configure(
            "Treeview.Heading",
            background="#eef3fb",
            foreground="#18212f",
            font=("Segoe UI Semibold", 10),
            relief="flat",
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(16, 14, 16, 10))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(3, weight=1)

        title_block = ttk.Frame(toolbar)
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="Pracovni asistent", style="Hero.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            title_block,
            text="E-maily, ukoly, faktury a schvalovani na jednom miste.",
            style="HeroSub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(
            toolbar,
            text="Obnovit",
            style="Secondary.TButton",
            command=self.refresh_all,
        ).grid(row=0, column=1, padx=(12, 6), sticky="e")
        self.sync_button = ttk.Button(
            toolbar,
            text="Synchronizovat",
            style="Primary.TButton",
            command=self.sync_once,
        )
        self.sync_button.grid(row=0, column=2, padx=6, sticky="e")
        self.sync_progress = ttk.Progressbar(
            toolbar,
            orient="horizontal",
            mode="determinate",
            length=220,
        )
        self.sync_progress.grid(row=0, column=3, padx=(12, 6), sticky="e")
        ttk.Label(toolbar, textvariable=self.sync_progress_var).grid(
            row=0, column=4, sticky="w"
        )
        ttk.Label(toolbar, text="Filtr e-mailu:").grid(row=0, column=5, padx=(12, 6), sticky="e")
        filter_box = ttk.Combobox(
            toolbar,
            textvariable=self.email_filter_var,
            values=("K reseni", "Vse", "Newslettery", "Neroztridene", "Archiv"),
            state="readonly",
            width=14,
        )
        filter_box.grid(row=0, column=6, sticky="e")
        filter_box.bind("<<ComboboxSelected>>", lambda event: self.refresh_all())
        toolbar.columnconfigure(7, weight=1)
        ttk.Label(toolbar, textvariable=self.summary_var, style="Summary.TLabel").grid(
            row=0, column=7, sticky="e"
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))

        self.overview_tab = ttk.Frame(self.notebook, padding=12)
        self.projects_tab = ttk.Frame(self.notebook, padding=12)
        self.tasks_tab = ttk.Frame(self.notebook, padding=12)
        self.emails_tab = ttk.Frame(self.notebook, padding=12)
        self.invoices_tab = ttk.Frame(self.notebook, padding=12)
        self.reminders_tab = ttk.Frame(self.notebook, padding=12)
        self.archive_tab = ttk.Frame(self.notebook, padding=12)
        self.approvals_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.overview_tab, text="Nezpracovane")
        self.notebook.add(self.projects_tab, text="Zakazky")
        self.notebook.add(self.tasks_tab, text="Ukoly")
        self.notebook.add(self.emails_tab, text="E-maily")
        self.notebook.add(self.invoices_tab, text="Faktury")
        self.notebook.add(self.reminders_tab, text="Pripominky")
        self.notebook.add(self.archive_tab, text="Archiv")
        self.notebook.add(self.approvals_tab, text="Schvalování")

        self._build_overview_tab()
        self._build_projects_tab()
        self._build_tasks_tab()
        self._build_emails_tab()
        self._build_invoices_tab()
        self._build_reminders_tab()
        self._build_archive_tab()
        self._build_approvals_tab()

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padding=(12, 6),
        )
        status_bar.grid(row=2, column=0, sticky="ew")

    def _build_overview_tab(self) -> None:
        self.overview_tab.columnconfigure(0, weight=1)
        self.overview_tab.columnconfigure(1, weight=1)
        self.overview_tab.rowconfigure(1, weight=1)

        cards = ttk.Frame(self.overview_tab)
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for column in range(4):
            cards.columnconfigure(column, weight=1)

        self.emails_count_var = StringVar(value="0")
        self.approvals_count_var = StringVar(value="0")
        self.tasks_count_var = StringVar(value="0")
        self.invoices_count_var = StringVar(value="0")

        self._create_stat_card(cards, 0, "E-maily", self.emails_count_var)
        self._create_stat_card(cards, 1, "Čeká na schválení", self.approvals_count_var)
        self._create_stat_card(cards, 2, "Ukoly", self.tasks_count_var)
        self._create_stat_card(cards, 3, "Faktury", self.invoices_count_var)

        recent_frame = ttk.LabelFrame(
            self.overview_tab,
            text="Nezpracovane",
            padding=8,
            style="Card.TLabelframe",
        )
        recent_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(0, weight=1)

        self.today_tree = ttk.Treeview(
            recent_frame,
            columns=("kind", "title", "due", "status"),
            show="headings",
            height=16,
            selectmode="extended",
        )
        for column, width in (
            ("kind", 120),
            ("title", 360),
            ("due", 160),
            ("status", 130),
        ):
            title = {
                "kind": "Typ",
                "title": "Polozka",
                "due": "Termin",
                "status": "Stav",
            }[column]
            self.today_tree.heading(column, text=title)
            self.today_tree.column(column, width=width, anchor="w")
        self.today_tree.grid(row=0, column=0, sticky="nsew")
        self.today_tree.bind("<<TreeviewSelect>>", self._on_today_selected)
        recent_scroll = ttk.Scrollbar(
            recent_frame,
            orient=VERTICAL,
            command=self.today_tree.yview,
        )
        recent_scroll.grid(row=0, column=1, sticky="ns")
        self.today_tree.configure(yscrollcommand=recent_scroll.set)
        self.today_tree.tag_configure("completed", background="#dff7df")
        self.today_tree.tag_configure("attention", background="#fff6d6")

        pending_frame = ttk.LabelFrame(
            self.overview_tab,
            text="Detail vybrane polozky",
            padding=8,
            style="Card.TLabelframe",
        )
        pending_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        pending_frame.columnconfigure(0, weight=1)
        pending_frame.rowconfigure(1, weight=1)

        today_actions = ttk.Frame(pending_frame)
        today_actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            today_actions,
            text="Na ukol",
            style="Secondary.TButton",
            command=self.today_mark_as_task,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            today_actions,
            text="Na fakturu",
            style="Secondary.TButton",
            command=self.today_mark_as_invoice,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            today_actions,
            text="Jen evidovat",
            style="Secondary.TButton",
            command=self.today_mark_as_tracked,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            today_actions,
            text="Dokoncit ukol",
            style="Secondary.TButton",
            command=self.today_complete_task,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            today_actions,
            text="Archivovat",
            style="Secondary.TButton",
            command=self.today_archive_selected,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            today_actions,
            text="Otevrit e-mail",
            style="Secondary.TButton",
            command=self.open_selected_source_email,
        ).pack(side=LEFT)

        self.today_detail = self._create_text(pending_frame)
        self.today_detail.grid(row=1, column=0, sticky="nsew")

    def _create_stat_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        variable: ttk.StringVar,
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=12, style="Card.TLabelframe")
        frame.grid(row=0, column=column, sticky="ew", padx=6)
        ttk.Label(frame, textvariable=variable, font=("Segoe UI", 20, "bold")).pack(anchor="w")

    def _build_emails_tab(self) -> None:
        self.emails_tab.columnconfigure(0, weight=5)
        self.emails_tab.columnconfigure(1, weight=6)
        self.emails_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.emails_tab, text="E-maily", padding=8, style="Card.TLabelframe"
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.email_tree = ttk.Treeview(
            list_frame,
            columns=("received", "sender", "subject", "category"),
            show="headings",
            selectmode="extended",
        )
        for column, width in (
            ("received", 125),
            ("sender", 170),
            ("subject", 260),
            ("category", 95),
        ):
            header_text = {
                "received": "Přijato",
                "sender": "Odesílatel",
                "subject": "Předmět",
                "category": "Kategorie",
            }[column]
            self.email_tree.heading(column, text=header_text)
            self.email_tree.column(column, width=width, anchor="w")
        self.email_tree.grid(row=0, column=0, sticky="nsew")
        self.email_tree.bind("<<TreeviewSelect>>", self._on_email_selected)
        email_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.email_tree.yview)
        email_scroll.grid(row=0, column=1, sticky="ns")
        self.email_tree.configure(yscrollcommand=email_scroll.set)
        self.email_tree.tag_configure("completed", background="#dff7df")
        self.email_tree.tag_configure("attention", background="#fff6d6")

        detail_frame = ttk.LabelFrame(
            self.emails_tab, text="Vybrany e-mail", padding=8, style="Card.TLabelframe"
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(2, weight=1)

        primary_actions = ttk.Frame(detail_frame)
        primary_actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(
            primary_actions,
            text="Na ukol",
            style="Secondary.TButton",
            command=self.create_task_from_selected_email,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            primary_actions,
            text="Na fakturu",
            style="Secondary.TButton",
            command=self.create_invoice_from_selected_email,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            primary_actions,
            text="Evidovat",
            style="Secondary.TButton",
            command=self.mark_selected_email_as_tracked,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            primary_actions,
            text="Do kalendare",
            style="Secondary.TButton",
            command=self.create_calendar_event_from_selected_email,
        ).pack(side=LEFT)
        ttk.Button(
            primary_actions,
            text="Archivovat",
            style="Secondary.TButton",
            command=self.archive_selected_emails,
        ).pack(side=LEFT, padx=(6, 0))

        self.email_meta = ttk.Label(detail_frame, justify=LEFT)
        self.email_meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        body_frame = ttk.LabelFrame(
            detail_frame, text="Obsah e-mailu", padding=6, style="Card.TLabelframe"
        )
        body_frame.grid(row=2, column=0, sticky="nsew")
        body_frame.columnconfigure(0, weight=1)
        body_frame.rowconfigure(0, weight=1)
        self.email_body = self._create_text(body_frame)
        self.email_body.grid(row=0, column=0, sticky="nsew")

    def _build_projects_tab(self) -> None:
        self.projects_tab.columnconfigure(0, weight=1)
        self.projects_tab.columnconfigure(1, weight=2)
        self.projects_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.projects_tab, text="Zakazky", padding=8, style="Card.TLabelframe"
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.project_tree = ttk.Treeview(
            list_frame,
            columns=("name", "status", "emails", "items"),
            show="headings",
        )
        for column, width in (
            ("name", 230),
            ("status", 120),
            ("emails", 80),
            ("items", 100),
        ):
            header_text = {
                "name": "Nazev",
                "status": "Stav",
                "emails": "E-maily",
                "items": "Ukoly+Faktury",
            }[column]
            self.project_tree.heading(column, text=header_text)
            self.project_tree.column(column, width=width, anchor="w")
        self.project_tree.grid(row=0, column=0, sticky="nsew")
        self.project_tree.bind("<<TreeviewSelect>>", self._on_project_selected)
        project_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.project_tree.yview)
        project_scroll.grid(row=0, column=1, sticky="ns")
        self.project_tree.configure(yscrollcommand=project_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.projects_tab, text="Detail zakazky", padding=8, style="Card.TLabelframe"
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)
        detail_frame.rowconfigure(3, weight=2)

        actions = ttk.Frame(detail_frame)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            actions,
            text="Nova zakazka",
            style="Primary.TButton",
            command=self.create_project_from_dialog,
        ).pack(side=LEFT)
        ttk.Button(
            actions,
            text="Otevrit vybrany e-mail",
            style="Secondary.TButton",
            command=self.open_selected_project_email,
        ).pack(side=LEFT, padx=(6, 0))
        ttk.Label(actions, text="Stav:").pack(side=LEFT, padx=(12, 6))
        status_box = ttk.Combobox(
            actions,
            textvariable=self.project_status_var,
            values=("Nova", "Rozpracovana", "Cekajici", "Hotova"),
            state="readonly",
            width=14,
        )
        status_box.pack(side=LEFT)
        ttk.Button(
            actions,
            text="Ulozit stav",
            style="Secondary.TButton",
            command=self.update_selected_project_status,
        ).pack(side=LEFT, padx=(6, 0))
        ttk.Button(
            actions,
            text="Ulozit info",
            style="Secondary.TButton",
            command=self.save_project_notes,
        ).pack(side=LEFT, padx=(6, 0))

        self.project_detail = self._create_text(detail_frame)
        self.project_detail.grid(row=1, column=0, sticky="nsew")

        notes_frame = ttk.LabelFrame(
            detail_frame,
            text="Rucni info k zakazce",
            padding=8,
            style="Card.TLabelframe",
        )
        notes_frame.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        self.project_notes = Text(notes_frame, wrap="word", font=("Segoe UI", 10), height=5)
        self.project_notes.grid(row=0, column=0, sticky="nsew")
        notes_scroll = ttk.Scrollbar(notes_frame, orient=VERTICAL, command=self.project_notes.yview)
        notes_scroll.grid(row=0, column=1, sticky="ns")
        self.project_notes.configure(yscrollcommand=notes_scroll.set)

        project_emails_frame = ttk.LabelFrame(
            detail_frame,
            text="Prirazene e-maily",
            padding=8,
            style="Card.TLabelframe",
        )
        project_emails_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        project_emails_frame.columnconfigure(0, weight=1)
        project_emails_frame.columnconfigure(1, weight=2)
        project_emails_frame.rowconfigure(0, weight=1)

        self.project_email_tree = ttk.Treeview(
            project_emails_frame,
            columns=("received", "sender", "subject"),
            show="headings",
            height=10,
        )
        for column, width in (
            ("received", 140),
            ("sender", 180),
            ("subject", 320),
        ):
            header_text = {
                "received": "Prijato",
                "sender": "Odesilatel",
                "subject": "Predmet",
            }[column]
            self.project_email_tree.heading(column, text=header_text)
            self.project_email_tree.column(column, width=width, anchor="w")
        self.project_email_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.project_email_tree.bind("<<TreeviewSelect>>", self._on_project_email_selected)

        self.project_email_detail = self._create_text(project_emails_frame)
        self.project_email_detail.grid(row=0, column=1, sticky="nsew")

    def _build_tasks_tab(self) -> None:
        self.tasks_tab.columnconfigure(0, weight=1)
        self.tasks_tab.columnconfigure(1, weight=2)
        self.tasks_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.tasks_tab,
            text="Ukoly",
            padding=8,
            style="Card.TLabelframe",
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.task_tree = ttk.Treeview(
            list_frame,
            columns=("priority", "title", "due_date", "status"),
            show="headings",
            selectmode="extended",
        )
        for column, width in (
            ("priority", 90),
            ("title", 320),
            ("due_date", 130),
            ("status", 120),
        ):
            header_text = {
                "priority": "Priorita",
                "title": "Nazev",
                "due_date": "Termin",
                "status": "Stav",
            }[column]
            self.task_tree.heading(column, text=header_text)
            self.task_tree.column(column, width=width, anchor="w")
        self.task_tree.grid(row=0, column=0, sticky="nsew")
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)
        task_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.task_tree.yview)
        task_scroll.grid(row=0, column=1, sticky="ns")
        self.task_tree.configure(yscrollcommand=task_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.tasks_tab,
            text="Detail ukolu",
            padding=8,
            style="Card.TLabelframe",
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        actions = ttk.Frame(detail_frame)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            actions,
            text="Dokoncit",
            style="Primary.TButton",
            command=self.complete_selected_task,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            actions,
            text="Priradit k zakazce",
            style="Secondary.TButton",
            command=self.assign_selected_task_to_project,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            actions,
            text="Otevrit zdrojovy e-mail",
            style="Secondary.TButton",
            command=self.open_selected_source_email,
        ).pack(side=LEFT)
        ttk.Button(
            actions,
            text="Archivovat",
            style="Secondary.TButton",
            command=self.archive_selected_tasks,
        ).pack(side=LEFT, padx=(6, 0))

        self.task_detail = self._create_text(detail_frame)
        self.task_detail.grid(row=1, column=0, sticky="nsew")

    def _build_approvals_tab(self) -> None:
        self.approvals_tab.columnconfigure(0, weight=1)
        self.approvals_tab.columnconfigure(1, weight=2)
        self.approvals_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.approvals_tab, text="Schvalovani", padding=8, style="Card.TLabelframe"
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.approval_tree = ttk.Treeview(
            list_frame,
            columns=("id", "status", "action", "title"),
            show="headings",
        )
        for column, width in (
            ("id", 60),
            ("status", 90),
            ("action", 170),
            ("title", 300),
        ):
            header_text = {
                "id": "ID",
                "status": "Stav",
                "action": "Akce",
                "title": "Název",
            }[column]
            self.approval_tree.heading(column, text=header_text)
            self.approval_tree.column(column, width=width, anchor="w")
        self.approval_tree.grid(row=0, column=0, sticky="nsew")
        self.approval_tree.bind("<<TreeviewSelect>>", self._on_approval_selected)
        approval_scroll = ttk.Scrollbar(
            list_frame, orient=VERTICAL, command=self.approval_tree.yview
        )
        approval_scroll.grid(row=0, column=1, sticky="ns")
        self.approval_tree.configure(yscrollcommand=approval_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.approvals_tab, text="Detail navrhu", padding=8, style="Card.TLabelframe"
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        actions = ttk.Frame(detail_frame)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            actions,
            text="Schvalit",
            style="Primary.TButton",
            command=self.approve_selected,
        ).pack(
            side=LEFT, padx=(0, 6)
        )
        ttk.Button(
            actions,
            text="Zamitnout",
            style="Secondary.TButton",
            command=self.reject_selected,
        ).pack(side=LEFT)
        ttk.Button(
            actions,
            text="Otevrit zdrojovy e-mail",
            style="Secondary.TButton",
            command=self.open_selected_source_email,
        ).pack(side=LEFT, padx=(6, 0))

        self.approval_detail = self._create_text(detail_frame)
        self.approval_detail.grid(row=1, column=0, sticky="nsew")

    def _build_invoices_tab(self) -> None:
        self.invoices_tab.columnconfigure(0, weight=1)
        self.invoices_tab.columnconfigure(1, weight=2)
        self.invoices_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.invoices_tab, text="Faktury", padding=8, style="Card.TLabelframe"
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.invoice_tree = ttk.Treeview(
            list_frame,
            columns=("supplier", "number", "amount", "due_date", "status"),
            show="headings",
        )
        for column, width in (
            ("supplier", 220),
            ("number", 140),
            ("amount", 120),
            ("due_date", 120),
            ("status", 120),
        ):
            header_text = {
                "supplier": "Dodavatel",
                "number": "Číslo",
                "amount": "Celkova castka",
                "due_date": "Splatnost",
                "status": "Stav",
            }[column]
            self.invoice_tree.heading(column, text=header_text)
            self.invoice_tree.column(column, width=width, anchor="w")
        self.invoice_tree.grid(row=0, column=0, sticky="nsew")
        self.invoice_tree.bind("<<TreeviewSelect>>", self._on_invoice_selected)
        invoice_scroll = ttk.Scrollbar(
            list_frame,
            orient=VERTICAL,
            command=self.invoice_tree.yview,
        )
        invoice_scroll.grid(row=0, column=1, sticky="ns")
        self.invoice_tree.configure(yscrollcommand=invoice_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.invoices_tab, text="Detail faktury", padding=8, style="Card.TLabelframe"
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        actions = ttk.Frame(detail_frame)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            actions,
            text="Priradit k zakazce",
            style="Secondary.TButton",
            command=self.assign_selected_invoice_to_project,
        ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(
            actions,
            text="Otevrit PDF",
            style="Primary.TButton",
            command=self.open_invoice_attachment,
        ).pack(side=LEFT)
        ttk.Button(
            actions,
            text="Otevrit zdrojovy e-mail",
            style="Secondary.TButton",
            command=self.open_selected_source_email,
        ).pack(side=LEFT, padx=(6, 0))

        self.invoice_detail = self._create_text(detail_frame)
        self.invoice_detail.grid(row=1, column=0, sticky="nsew")

    def _build_reminders_tab(self) -> None:
        self.reminders_tab.columnconfigure(0, weight=1)
        self.reminders_tab.columnconfigure(1, weight=2)
        self.reminders_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.reminders_tab, text="Pripominky", padding=8, style="Card.TLabelframe"
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.reminder_tree = ttk.Treeview(
            list_frame,
            columns=("title", "remind_at", "related_type", "status"),
            show="headings",
        )
        for column, width in (
            ("title", 280),
            ("remind_at", 170),
            ("related_type", 120),
            ("status", 120),
        ):
            header_text = {
                "title": "Nazev",
                "remind_at": "Termin",
                "related_type": "Vazba",
                "status": "Stav",
            }[column]
            self.reminder_tree.heading(column, text=header_text)
            self.reminder_tree.column(column, width=width, anchor="w")
        self.reminder_tree.grid(row=0, column=0, sticky="nsew")
        self.reminder_tree.bind("<<TreeviewSelect>>", self._on_reminder_selected)
        reminder_scroll = ttk.Scrollbar(
            list_frame,
            orient=VERTICAL,
            command=self.reminder_tree.yview,
        )
        reminder_scroll.grid(row=0, column=1, sticky="ns")
        self.reminder_tree.configure(yscrollcommand=reminder_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.reminders_tab, text="Detail pripominky", padding=8, style="Card.TLabelframe"
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)

        self.reminder_detail = self._create_text(detail_frame)
        self.reminder_detail.grid(row=0, column=0, sticky="nsew")

    def _create_text(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = Text(frame, wrap="word", font=("Segoe UI", 10))
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient=VERTICAL, command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set)
        text.configure(state="disabled")
        frame.text_widget = text  # type: ignore[attr-defined]
        return frame

    def refresh_all(self) -> None:
        updated_attachments = self.invoice_service.backfill_attachment_paths()
        self.email_items = list(crud.list_emails(self.config))
        self.approval_items = list(self.approval_service.list_items())
        self.invoice_items = list(self.invoice_service.list_invoices())
        self.project_items = list(self.project_service.list_projects())
        self.task_items = list(self.task_service.list_tasks())
        self.reminder_items = list(self.reminder_service.list_reminders())

        self._refresh_summary(
            email_count=len(self.email_items),
            approval_count=len([item for item in self.approval_items if item.status == "pending"]),
            task_count=len(self.task_items),
            invoice_count=len(self.invoice_items),
        )
        self._refresh_overview(
            self.email_items,
            self.approval_items,
            self.task_items,
            self.invoice_items,
            self.reminder_items,
        )
        self._refresh_projects(self.project_items)
        self._refresh_tasks(self.task_items)
        self._refresh_emails(self.email_items)
        self._refresh_invoices(self.invoice_items)
        self._refresh_reminders(self.reminder_items)
        self._refresh_archive(self.email_items, self.task_items)
        self._refresh_approvals(self.approval_items)
        if updated_attachments:
            self.status_var.set(f"Data obnovena | doplneny PDF odkazy: {updated_attachments}")
        else:
            self.status_var.set("Data obnovena")

    def _refresh_projects(self, projects: list[ProjectModel]) -> None:
        for item_id in self.project_tree.get_children():
            self.project_tree.delete(item_id)

        for project in projects:
            emails, tasks, invoices, _, _ = self.project_service.get_project_summary(project.id)
            self.project_tree.insert(
                "",
                END,
                iid=str(project.id),
                values=(
                    project.name,
                    self._format_status(project.status),
                    len(emails),
                    len(tasks) + len(invoices),
                ),
            )

        if self.selected_project_id is not None and self.project_tree.exists(str(self.selected_project_id)):
            self.project_tree.selection_set(str(self.selected_project_id))
            self.project_tree.focus(str(self.selected_project_id))
            self._show_project_detail(self.selected_project_id)
        elif projects:
            self.selected_project_id = projects[0].id
            self.project_tree.selection_set(str(projects[0].id))
            self.project_tree.focus(str(projects[0].id))
            self._show_project_detail(projects[0].id)
        else:
            self._set_text(self.project_detail, "Zadne zakazky zatim nejsou vytvorene.")
            self._set_text(self.project_email_detail, "Pro vybranou zakazku tu uvidis e-maily.")
            self.project_notes.delete("1.0", END)

    def _refresh_project_emails(self, emails: list[EmailModel]) -> None:
        for item_id in self.project_email_tree.get_children():
            self.project_email_tree.delete(item_id)

        for email in emails:
            self.project_email_tree.insert(
                "",
                END,
                iid=email.id,
                values=(self._format_datetime_value(email.received_at), email.sender, email.subject),
            )

        if self.selected_project_email_id and self.project_email_tree.exists(self.selected_project_email_id):
            self.project_email_tree.selection_set(self.selected_project_email_id)
            self.project_email_tree.focus(self.selected_project_email_id)
            self._show_project_email_detail(self.selected_project_email_id)
        elif emails:
            self.selected_project_email_id = emails[0].id
            self.project_email_tree.selection_set(emails[0].id)
            self.project_email_tree.focus(emails[0].id)
            self._show_project_email_detail(emails[0].id)
        else:
            self.selected_project_email_id = None
            self._set_text(self.project_email_detail, "K teto zakazce zatim nejsou prirazene zadne e-maily.")

    def _refresh_summary(
        self,
        email_count: int,
        approval_count: int,
        task_count: int,
        invoice_count: int,
    ) -> None:
        self.emails_count_var.set(str(email_count))
        self.approvals_count_var.set(str(approval_count))
        self.tasks_count_var.set(str(task_count))
        self.invoices_count_var.set(str(invoice_count))
        self.summary_var.set(
            f"E-maily {email_count} | Schvaleni {approval_count} | Ukoly {task_count} | Faktury {invoice_count}"
        )

    def _refresh_overview(
        self,
        emails: list[EmailModel],
        approvals: list[ApprovalItemModel],
        tasks: list[TaskModel],
        invoices: list[InvoiceModel],
        reminders: list[ReminderModel],
    ) -> None:
        for item_id in self.today_tree.get_children():
            self.today_tree.delete(item_id)

        for email in emails:
            if email.status == "archived":
                continue
            if email.category != "uncategorized":
                continue
            today_id = f"email:{email.id}"
            email_tags = self._email_row_tags(email)
            self.today_tree.insert(
                "",
                END,
                iid=today_id,
                values=(
                    "E-mail",
                    email.subject,
                    self._format_datetime_value(email.received_at),
                    self._format_category(email.category),
                ),
                tags=email_tags,
            )

        for task in tasks:
            if task.status == "done":
                continue
            today_id = f"task:{task.id}"
            tags = ("attention",)
            self.today_tree.insert(
                "",
                END,
                iid=today_id,
                values=(
                    "Ukol",
                    task.title,
                    self._format_datetime_value(task.due_date),
                    self._format_status(task.status),
                ),
                tags=tags,
            )

        if self.selected_today_item and self.today_tree.exists(self.selected_today_item):
            self.today_tree.selection_set(self.selected_today_item)
            self.today_tree.focus(self.selected_today_item)
            self._show_today_detail(self.selected_today_item)
        elif self.today_tree.get_children():
            first_id = self.today_tree.get_children()[0]
            self.selected_today_item = str(first_id)
            self.today_tree.selection_set(first_id)
            self.today_tree.focus(first_id)
            self._show_today_detail(str(first_id))
        else:
            self._set_text(self.today_detail, "Nejsou tu zadne nezpracovane e-maily ani otevrene ukoly.")

    def _refresh_tasks(self, tasks: list[TaskModel]) -> None:
        for item_id in self.task_tree.get_children():
            self.task_tree.delete(item_id)

        for task in tasks:
            self.task_tree.insert(
                "",
                END,
                iid=str(task.id),
                values=(
                    self._format_priority(task.priority),
                    task.title,
                    self._format_datetime_value(task.due_date),
                    self._format_status(task.status),
                ),
            )

        if self.selected_task_id is not None and self.task_tree.exists(str(self.selected_task_id)):
            self.task_tree.selection_set(str(self.selected_task_id))
            self.task_tree.focus(str(self.selected_task_id))
            self._show_task_detail(self.selected_task_id)
        elif tasks:
            self.selected_task_id = tasks[0].id
            self.task_tree.selection_set(str(tasks[0].id))
            self.task_tree.focus(str(tasks[0].id))
            self._show_task_detail(tasks[0].id)
        else:
            self._set_text(self.task_detail, "Zadne ukoly zatim nejsou ulozene.")

    def _refresh_reminders(self, reminders: list[ReminderModel]) -> None:
        for item_id in self.reminder_tree.get_children():
            self.reminder_tree.delete(item_id)

        for reminder in reminders:
            self.reminder_tree.insert(
                "",
                END,
                iid=str(reminder.id),
                values=(
                    reminder.title,
                    self._format_datetime_value(reminder.remind_at),
                    self._format_related_type(reminder.related_type),
                    self._format_status(reminder.status),
                ),
            )

        if self.selected_reminder_id is not None and self.reminder_tree.exists(
            str(self.selected_reminder_id)
        ):
            self.reminder_tree.selection_set(str(self.selected_reminder_id))
            self.reminder_tree.focus(str(self.selected_reminder_id))
            self._show_reminder_detail(self.selected_reminder_id)
        elif reminders:
            self.selected_reminder_id = reminders[0].id
            self.reminder_tree.selection_set(str(reminders[0].id))
            self.reminder_tree.focus(str(reminders[0].id))
            self._show_reminder_detail(reminders[0].id)
        else:
            self._set_text(self.reminder_detail, "Zadne pripominky zatim nejsou ulozene.")

    def _refresh_emails(self, emails: list[EmailModel]) -> None:
        for item_id in self.email_tree.get_children():
            self.email_tree.delete(item_id)

        visible_emails = self._filter_emails(emails)
        for email in visible_emails:
            self.email_tree.insert(
                "",
                END,
                iid=email.id,
                values=(
                    self._format_datetime_value(email.received_at),
                    email.sender,
                    email.subject,
                    self._format_category(email.category),
                ),
                tags=self._email_row_tags(email),
            )

        if self.selected_email_id and self.email_tree.exists(self.selected_email_id):
            self.email_tree.selection_set(self.selected_email_id)
            self.email_tree.focus(self.selected_email_id)
            self._show_email_detail(self.selected_email_id)
        elif visible_emails:
            self.selected_email_id = visible_emails[0].id
            self.email_tree.selection_set(visible_emails[0].id)
            self.email_tree.focus(visible_emails[0].id)
            self._show_email_detail(visible_emails[0].id)
        else:
            self._set_text(self.email_body, "Zadne e-maily nejsou nactene.")
            self.email_meta.configure(text="")
            self.selected_email_id = None

    def _refresh_invoices(self, invoices: list[InvoiceModel]) -> None:
        for item_id in self.invoice_tree.get_children():
            self.invoice_tree.delete(item_id)

        for invoice in invoices:
            amount_text = (
                f"{invoice.amount:.2f} {invoice.currency}"
                if invoice.amount is not None
                else f"- {invoice.currency}"
            )
            self.invoice_tree.insert(
                "",
                END,
                iid=str(invoice.id),
                values=(
                    invoice.supplier,
                    invoice.invoice_number or "-",
                    amount_text,
                    self._format_datetime_value(invoice.due_date),
                    self._format_status(invoice.status),
                ),
            )

        if self.selected_invoice_id is not None and self.invoice_tree.exists(
            str(self.selected_invoice_id)
        ):
            self.invoice_tree.selection_set(str(self.selected_invoice_id))
            self.invoice_tree.focus(str(self.selected_invoice_id))
            self._show_invoice_detail(self.selected_invoice_id)
        elif invoices:
            self.selected_invoice_id = invoices[0].id
            self.invoice_tree.selection_set(str(invoices[0].id))
            self.invoice_tree.focus(str(invoices[0].id))
            self._show_invoice_detail(invoices[0].id)
        else:
            self._set_text(self.invoice_detail, "Žádné faktury nejsou uložené.")

    def _refresh_approvals(self, approvals: list[ApprovalItemModel]) -> None:
        for item_id in self.approval_tree.get_children():
            self.approval_tree.delete(item_id)

        for item in approvals:
            self.approval_tree.insert(
                "",
                END,
                iid=str(item.id),
                values=(
                    item.id,
                    self._format_status(item.status),
                    self._format_action_type(item.action_type),
                    item.title,
                ),
            )

        if self.selected_approval_id is not None and self.approval_tree.exists(
            str(self.selected_approval_id)
        ):
            self.approval_tree.selection_set(str(self.selected_approval_id))
            self.approval_tree.focus(str(self.selected_approval_id))
            self._show_approval_detail(self.selected_approval_id)
        elif approvals:
            self.selected_approval_id = approvals[0].id
            self.approval_tree.selection_set(str(approvals[0].id))
            self.approval_tree.focus(str(approvals[0].id))
            self._show_approval_detail(approvals[0].id)
        else:
            self._set_text(self.approval_detail, "Žádné návrhy nejsou načtené.")

    def _on_email_selected(self, event: object) -> None:
        selection = self.email_tree.selection()
        if not selection:
            return
        self.selected_email_id = selection[0]
        self._show_email_detail(selection[0])

    def _on_project_selected(self, event: object) -> None:
        selection = self.project_tree.selection()
        if not selection:
            return
        self.selected_project_id = int(selection[0])
        self._show_project_detail(self.selected_project_id)

    def _on_project_email_selected(self, event: object) -> None:
        selection = self.project_email_tree.selection()
        if not selection:
            return
        self.selected_project_email_id = selection[0]
        self._show_project_email_detail(self.selected_project_email_id)

    def _on_today_selected(self, event: object) -> None:
        selection = self.today_tree.selection()
        if not selection:
            return
        self.selected_today_item = str(selection[0])
        self._show_today_detail(self.selected_today_item)

    def _on_task_selected(self, event: object) -> None:
        selection = self.task_tree.selection()
        if not selection:
            return
        self.selected_task_id = int(selection[0])
        self._show_task_detail(self.selected_task_id)

    def _on_reminder_selected(self, event: object) -> None:
        selection = self.reminder_tree.selection()
        if not selection:
            return
        self.selected_reminder_id = int(selection[0])
        self._show_reminder_detail(self.selected_reminder_id)

    def _on_approval_selected(self, event: object) -> None:
        selection = self.approval_tree.selection()
        if not selection:
            return
        self.selected_approval_id = int(selection[0])
        self._show_approval_detail(self.selected_approval_id)

    def _on_invoice_selected(self, event: object) -> None:
        selection = self.invoice_tree.selection()
        if not selection:
            return
        self.selected_invoice_id = int(selection[0])
        self._show_invoice_detail(self.selected_invoice_id)

    def _show_email_detail(self, email_id: str) -> None:
        email = crud.get_email(self.config, email_id)
        if email is None:
            self.email_meta.configure(text="E-mail nebyl nalezen.")
            self._set_text(self.email_body, "")
            return

        attachments = "\n".join(email.attachments) if email.attachments else "zadne"
        meta = (
            f"Predmet: {email.subject}\n"
            f"Odesilatel: {email.sender}\n"
            f"Prijato: {self._format_datetime_value(email.received_at)}\n"
            f"Kategorie: {self._format_category(email.category)}\n"
            f"Priorita: {self._format_priority(email.priority)}\n"
            f"Stav: {self._format_status(email.status)}\n"
            f"Zakazka: {self._project_name(email.project_id)}\n"
            f"Prilohy:\n{attachments}\n"
        )
        self.email_meta.configure(text=meta)
        self._set_text(self.email_body, self._display_email_body(email.body))
        self.current_source_email_id = email.id

    def _show_project_detail(self, project_id: int) -> None:
        project = next((item for item in self.project_items if item.id == project_id), None)
        if project is None:
            self._set_text(self.project_detail, "Zakazka nebyla nalezena.")
            self._set_text(self.project_email_detail, "Zakazka nebyla nalezena.")
            return

        emails, tasks, invoices, work_logs, _ = self.project_service.get_project_summary(project.id)
        finance = self.project_service.get_project_finance_summary(project.id)
        task_lines = [f"- {task.title}" for task in tasks[:8]] or ["- zadne"]
        invoice_lines = [f"- {invoice.invoice_number or invoice.supplier}" for invoice in invoices[:8]] or [
            "- zadne"
        ]
        timeline_entries: list[tuple[str, str, str]] = []
        for email in emails:
            timeline_entries.append(
                (email.received_at, "E-mail", f"{self._format_datetime_value(email.received_at)} | {email.subject}")
            )
        for task in tasks:
            timeline_entries.append(
                (task.created_at, "Ukol", f"{self._format_datetime_value(task.created_at)} | {task.title}")
            )
        for invoice in invoices:
            timeline_entries.append(
                (
                    invoice.created_at,
                    "Faktura",
                    f"{self._format_datetime_value(invoice.created_at)} | {invoice.invoice_number or invoice.supplier}",
                )
            )
        for work_log in work_logs:
            timeline_entries.append(
                (
                    work_log.created_at,
                    "Vykaz",
                    (
                        f"{self._format_datetime_value(work_log.created_at)} | "
                        f"{work_log.hours:.2f} h | pracovnik #{work_log.worker_id}"
                    ),
                )
            )
        timeline_entries.sort(key=lambda item: item[0], reverse=True)
        timeline_lines = [f"- {item[2]}" for item in timeline_entries[:12]] or ["- zadne"]

        detail = (
            f"ID: {project.id}\n"
            f"Nazev: {project.name}\n"
            f"Kod: {project.code or '-'}\n"
            f"Zakaznik: {project.customer_name or '-'}\n"
            f"Kontakt: {project.contact_person or '-'} | {project.contact_email or '-'} | {project.contact_phone or '-'}\n"
            f"Adresa: {project.address or '-'}\n"
            f"Stav: {self._format_status(project.status)}\n"
            f"Priorita: {self._format_priority(project.priority)}\n"
            f"Plan: {self._format_datetime_value(project.planned_start_at)} -> {self._format_datetime_value(project.planned_end_at)}\n"
            f"Popis: {project.description or '-'}\n\n"
            f"E-maily: {len(emails)}\n"
            f"Ukoly ({len(tasks)}):\n" + "\n".join(task_lines) + "\n\n"
            f"Faktury ({len(invoices)}):\n" + "\n".join(invoice_lines) + "\n\n"
            f"Finance:\n"
            f"- Faktury celkem: {finance['invoice_total']:.2f}\n"
            f"- Vyplaty: {finance['payout_total']:.2f}\n"
            f"- Material: {finance['material_total']:.2f}\n"
            f"- Zustatek: {finance['balance']:.2f}\n\n"
            f"Timeline:\n" + "\n".join(timeline_lines)
        )
        self._set_text(self.project_detail, detail)
        self.project_status_var.set(self._project_status_label(project.status))
        self.project_notes.delete("1.0", END)
        self.project_notes.insert("1.0", project.description or "")
        self._refresh_project_emails(emails)

    def _show_project_email_detail(self, email_id: str) -> None:
        email = crud.get_email(self.config, email_id)
        if email is None:
            self._set_text(self.project_email_detail, "E-mail nebyl nalezen.")
            return

        attachments = "\n".join(email.attachments) if email.attachments else "-"
        detail = (
            f"Predmet: {email.subject}\n"
            f"Odesilatel: {email.sender}\n"
            f"Prijato: {self._format_datetime_value(email.received_at)}\n"
            f"Kategorie: {self._format_category(email.category)}\n"
            f"Shrnuti:\n{email.summary or '-'}\n\n"
            f"Telo zpravy:\n{self._display_email_body(email.body)}\n\n"
            f"Prilohy:\n{attachments}"
        )
        self._set_text(self.project_email_detail, detail)

    def _show_today_detail(self, item_key: str) -> None:
        item_type, _, raw_id = item_key.partition(":")
        detail = "Polozka nebyla nalezena."
        self.current_source_email_id = None

        if item_type == "email":
            email = crud.get_email(self.config, raw_id)
            if email is not None:
                detail = (
                    f"Polozka: Nezarazeny e-mail\n"
                    f"Predmet: {email.subject}\n"
                    f"Odesilatel: {email.sender}\n"
                    f"Prijato: {self._format_datetime_value(email.received_at)}\n"
                    f"Kategorie: {self._format_category(email.category)}\n"
                    f"Stav: {self._format_status(email.status)}\n"
                    f"Zakazka: {self._project_name(email.project_id)}\n\n"
                    f"Shrnuti:\n{email.summary or '-'}"
                )
                self.current_source_email_id = email.id
        elif item_type == "task":
            try:
                task_id = int(raw_id)
            except ValueError:
                task_id = 0
            task = next((item for item in self.task_items if item.id == task_id), None)
            if task is not None:
                detail = (
                    f"Polozka: Nesplneny ukol\n"
                    f"Nazev: {task.title}\n"
                    f"Priorita: {self._format_priority(task.priority)}\n"
                    f"Termin: {self._format_datetime_value(task.due_date)}\n"
                    f"Stav: {self._format_status(task.status)}\n"
                    f"Zakazka: {self._project_name(task.project_id)}\n"
                    f"Zdrojovy e-mail: {task.source_email_id or '-'}\n\n"
                    f"Popis:\n{task.description or '-'}"
                )
                self.current_source_email_id = task.source_email_id

        self._set_text(self.today_detail, detail)

    def _show_approval_detail(self, approval_id: int) -> None:
        item = self.approval_service.get_item(approval_id)
        if item is None:
            self._set_text(self.approval_detail, "Návrh nebyl nalezen.")
            self.current_source_email_id = None
            return

        detail = (
            f"Id: {item.id}\n"
            f"Stav: {self._format_status(item.status)}\n"
            f"Akce: {self._format_action_type(item.action_type)}\n"
            f"Název: {item.title}\n"
            f"Zdrojový e-mail: {item.source_email_id or '-'}\n"
            f"Důvod: {item.reason or '-'}\n\n"
            f"Data návrhu:\n{json.dumps(item.payload, ensure_ascii=False, indent=2)}"
        )
        self._set_text(self.approval_detail, detail)
        self.current_source_email_id = item.source_email_id

    def _show_invoice_detail(self, invoice_id: int) -> None:
        invoice = next((item for item in self.invoice_items if item.id == invoice_id), None)
        if invoice is None:
            self._set_text(self.invoice_detail, "Faktura nebyla nalezena.")
            self.current_source_email_id = None
            return

        self._set_text(self.invoice_detail, self._format_invoice_detail(invoice))
        self.current_source_email_id = invoice.source_email_id

    def _show_task_detail(self, task_id: int) -> None:
        task = next((item for item in self.task_items if item.id == task_id), None)
        if task is None:
            self._set_text(self.task_detail, "Ukol nebyl nalezen.")
            self.current_source_email_id = None
            return
        self._set_text(self.task_detail, self._format_task_detail(task))
        self.current_source_email_id = task.source_email_id

    def _show_reminder_detail(self, reminder_id: int) -> None:
        reminder = next((item for item in self.reminder_items if item.id == reminder_id), None)
        if reminder is None:
            self._set_text(self.reminder_detail, "Pripominka nebyla nalezena.")
            return

        detail = (
            f"ID: {reminder.id}\n"
            f"Nazev: {reminder.title}\n"
            f"Termin: {self._format_datetime_value(reminder.remind_at)}\n"
            f"Stav: {self._format_status(reminder.status)}\n"
            f"Vazba: {self._format_related_type(reminder.related_type)}\n"
            f"ID vazby: {reminder.related_id or '-'}\n\n"
            f"Poznamky:\n{reminder.notes or '-'}"
        )
        self._set_text(self.reminder_detail, detail)

    def open_invoice_attachment(self) -> None:
        if self.selected_invoice_id is None:
            messagebox.showinfo("Faktury", "Nejprve vyber fakturu.")
            return

        invoice = next(
            (item for item in self.invoice_items if item.id == self.selected_invoice_id),
            None,
        )
        if invoice is None or not invoice.attachment_path:
            messagebox.showinfo("Faktury", "Tato faktura nema ulozenou PDF prilohu.")
            return

        attachment_path = invoice.attachment_path
        if not os.path.exists(attachment_path):
            messagebox.showwarning("Faktury", f"Soubor nebyl nalezen:\n{attachment_path}")
            return

        try:
            os.startfile(attachment_path)
        except OSError as exc:
            messagebox.showerror("Faktury", f"PDF se nepodarilo otevrit:\n{exc}")

    def create_project_from_dialog(self) -> None:
        project = self._prompt_project()
        if project is None:
            return
        self.refresh_all()
        self.selected_project_id = project.id
        self.status_var.set(f"Zakazka {project.name} byla pripravena")

    def create_task_from_selected_email(self) -> None:
        email = self._get_selected_email_entity()
        if email is None:
            messagebox.showinfo("E-maily", "Nejprve vyber e-mail.")
            return
        self._create_task_from_email(email)

    def _create_task_from_email(self, email: Email) -> None:

        classification = EmailClassification(
            category="task",
            action="create_task",
            priority=email.priority,
            needs_reply=False,
            confidence=1.0,
        )
        parsed = self.parser_service.parse_message(email, classification)
        self.task_service.create_task(
            title=email.subject,
            description=parsed.summary or email.body[:500],
            priority=email.priority,
            due_date=parsed.requested_deadline,
            source_email_id=email.id,
            project_id=email.project_id,
        )
        crud.update_email_category(self.config, email.id, "task")
        crud.update_email_status(self.config, email.id, "confirmed")
        self.refresh_all()
        self.status_var.set(f"Z e-mailu byl vytvoren ukol: {email.subject}")

    def create_invoice_from_selected_email(self) -> None:
        email = self._get_selected_email_entity()
        if email is None:
            messagebox.showinfo("E-maily", "Nejprve vyber e-mail.")
            return
        self._create_invoice_from_email(email)

    def _create_invoice_from_email(self, email: Email) -> None:

        classification = EmailClassification(
            category="invoice",
            action="create_invoice",
            priority=email.priority,
            needs_reply=False,
            confidence=1.0,
        )
        parsed = self.parser_service.parse_message(email, classification)
        pdf_attachment = next(
            (attachment for attachment in email.attachments if attachment.lower().endswith(".pdf")),
            "",
        )
        self.invoice_service.create_invoice(
            supplier=parsed.company_name or parsed.contact or email.sender,
            invoice_number=parsed.invoice_number,
            amount=parsed.invoice_amount,
            currency=parsed.invoice_currency,
            due_date=parsed.invoice_due_date,
            source_email_id=email.id,
            attachment_path=pdf_attachment,
            project_id=email.project_id,
        )
        crud.update_email_category(self.config, email.id, "invoice")
        crud.update_email_status(self.config, email.id, "confirmed")
        if parsed.invoice_due_date:
            self.reminder_service.create_reminder(
                title=f"Splatnost faktury: {parsed.invoice_number or email.subject}",
                remind_at=parsed.invoice_due_date,
                notes=parsed.summary,
                related_type="invoice",
                related_id=email.id,
            )
        self.refresh_all()
        self.status_var.set(f"Z e-mailu byla zaevidovana faktura: {email.subject}")

    def mark_selected_email_as_tracked(self) -> None:
        email = self._get_selected_email_entity()
        if email is None:
            messagebox.showinfo("E-maily", "Nejprve vyber e-mail.")
            return
        self._mark_email_as_tracked(email.id)
        self.status_var.set(f"E-mail byl presunut do kategorie Jen evidovat: {email.subject}")

    def _mark_email_as_tracked(self, email_id: str) -> None:
        crud.update_email_category(self.config, email_id, "general")
        crud.update_email_status(self.config, email_id, "confirmed")
        self.refresh_all()

    def create_calendar_event_from_selected_email(self) -> None:
        email = self._get_selected_email_entity()
        if email is None:
            messagebox.showinfo("E-maily", "Nejprve vyber e-mail.")
            return
        self._create_calendar_event_from_email(email)

    def _create_calendar_event_from_email(self, email: Email) -> None:

        classification = EmailClassification(
            category="calendar",
            action="create_calendar_event",
            priority=email.priority,
            needs_reply=False,
            confidence=1.0,
        )
        parsed = self.parser_service.parse_message(email, classification)
        if not parsed.requested_deadline:
            messagebox.showinfo(
                "Kalendář",
                "V e-mailu nebyl nalezen termín. Nejprve ho doplň nebo použij návrh agenta.",
            )
            return

        self.calendar_service.create_event_proposal(
            title=email.subject,
            starts_at=parsed.requested_deadline,
            ends_at=parsed.requested_deadline,
            description=parsed.summary or email.body[:500],
            location=parsed.address,
            source_email_id=email.id,
        )
        crud.update_email_status(self.config, email.id, "confirmed")
        self.refresh_all()
        self.status_var.set(f"Z e-mailu byl vytvoren navrh do kalendare: {email.subject}")

    def complete_selected_task(self) -> None:
        if self.selected_task_id is None:
            messagebox.showinfo("Ukoly", "Nejprve vyber ukol.")
            return
        if not self.task_service.complete_task(self.selected_task_id):
            messagebox.showwarning("Ukoly", "Ukol se nepodarilo dokoncit.")
            return
        self.refresh_all()
        self.status_var.set(f"Ukol #{self.selected_task_id} byl oznacen jako hotovy")

    def update_selected_project_status(self) -> None:
        if self.selected_project_id is None:
            messagebox.showinfo("Zakazky", "Nejprve vyber zakazku.")
            return
        status = self._project_status_value(self.project_status_var.get())
        if not self.project_service.update_status(self.selected_project_id, status):
            messagebox.showwarning("Zakazky", "Stav zakazky se nepodarilo ulozit.")
            return
        self.refresh_all()
        self.status_var.set(f"Stav zakazky byl nastaven na {self.project_status_var.get()}")

    def save_project_notes(self) -> None:
        if self.selected_project_id is None:
            messagebox.showinfo("Zakazky", "Nejprve vyber zakazku.")
            return
        notes = self.project_notes.get("1.0", END).strip()
        if not self.project_service.update_description(self.selected_project_id, notes):
            messagebox.showwarning("Zakazky", "Info k zakazce se nepodarilo ulozit.")
            return
        self.refresh_all()
        self.status_var.set("Info k zakazce bylo ulozeno")

    def today_mark_as_task(self) -> None:
        email = self._get_today_email_entity()
        if email is None:
            messagebox.showinfo("Nezpracovane", "Tato akce je dostupna jen pro e-mail.")
            return
        self._create_task_from_email(email)

    def today_mark_as_invoice(self) -> None:
        email = self._get_today_email_entity()
        if email is None:
            messagebox.showinfo("Nezpracovane", "Tato akce je dostupna jen pro e-mail.")
            return
        self._create_invoice_from_email(email)

    def today_mark_as_tracked(self) -> None:
        email = self._get_today_email_entity()
        if email is None:
            messagebox.showinfo("Nezpracovane", "Tato akce je dostupna jen pro e-mail.")
            return
        self._mark_email_as_tracked(email.id)
        self.status_var.set(f"E-mail byl potvrzen jako Jen evidovat: {email.subject}")

    def today_complete_task(self) -> None:
        task_id = self._get_today_task_id()
        if task_id is None:
            messagebox.showinfo("Nezpracovane", "Tato akce je dostupna jen pro ukol.")
            return
        if not self.task_service.complete_task(task_id):
            messagebox.showwarning("Nezpracovane", "Ukol se nepodarilo dokoncit.")
            return
        self.refresh_all()
        self.status_var.set(f"Ukol #{task_id} byl oznacen jako hotovy")

    def assign_selected_email_to_project(self) -> None:
        if not self.selected_email_id:
            messagebox.showinfo("Zakazky", "Nejprve vyber e-mail.")
            return
        project = self._prompt_project()
        if project is None:
            return
        self.project_service.assign_email(self.selected_email_id, project.id)
        self.refresh_all()
        self.status_var.set(f"E-mail byl prirazen k zakazce {project.name}")

    def assign_selected_task_to_project(self) -> None:
        if self.selected_task_id is None:
            messagebox.showinfo("Zakazky", "Nejprve vyber ukol.")
            return
        project = self._prompt_project()
        if project is None:
            return
        self.project_service.assign_task(self.selected_task_id, project.id)
        self.refresh_all()
        self.status_var.set(f"Ukol byl prirazen k zakazce {project.name}")

    def assign_selected_invoice_to_project(self) -> None:
        if self.selected_invoice_id is None:
            messagebox.showinfo("Zakazky", "Nejprve vyber fakturu.")
            return
        project = self._prompt_project()
        if project is None:
            return
        self.project_service.assign_invoice(self.selected_invoice_id, project.id)
        self.refresh_all()
        self.status_var.set(f"Faktura byla prirazena k zakazce {project.name}")

    def open_selected_project_email(self) -> None:
        if not self.selected_project_email_id:
            messagebox.showinfo("Zakazky", "Nejprve vyber e-mail v zakazce.")
            return
        self._open_email_by_id(self.selected_project_email_id)

    def open_selected_source_email(self) -> None:
        if not self.current_source_email_id:
            messagebox.showinfo("E-maily", "K vybrane polozce neni navazany zdrojovy e-mail.")
            return
        self._open_email_by_id(self.current_source_email_id)

    def _open_email_by_id(self, email_id: str) -> None:
        email = crud.get_email(self.config, email_id)
        if email is None:
            messagebox.showwarning("E-maily", f"Zdrojovy e-mail nebyl nalezen:\n{email_id}")
            return

        self.notebook.select(self.emails_tab)
        self.selected_email_id = email.id
        self.email_filter_var.set("Vse")
        self._refresh_emails(self.email_items)
        if self.email_tree.exists(email.id):
            self.email_tree.selection_set(email.id)
            self.email_tree.focus(email.id)
        self._show_email_detail(email.id)
        self.status_var.set(f"Otevren zdrojovy e-mail {email.subject}")

    def _prompt_project(self) -> ProjectModel | None:
        known_projects = ", ".join(project.name for project in self.project_items[:8]) or "zadne"
        name = simpledialog.askstring(
            "Zakazka",
            f"Zadej nazev zakazky.\nExistujici: {known_projects}",
            parent=self.root,
        )
        if not name or not name.strip():
            return None
        return self.project_service.get_or_create_project(name.strip())

    def approve_selected(self) -> None:
        if self.selected_approval_id is None:
            messagebox.showinfo("Schválení", "Nejprve vyber návrh.")
            return

        approved = self.approval_service.approve_item(self.selected_approval_id)
        if not approved:
            messagebox.showwarning("Schválení", "Návrh se nepodařilo schválit.")
            return

        self.refresh_all()
        self.status_var.set(f"Návrh #{self.selected_approval_id} byl schválen")

    def reject_selected(self) -> None:
        if self.selected_approval_id is None:
            messagebox.showinfo("Zamítnutí", "Nejprve vyber návrh.")
            return

        rejected = self.approval_service.reject_item(self.selected_approval_id)
        if not rejected:
            messagebox.showwarning("Zamítnutí", "Návrh se nepodařilo zamítnout.")
            return

        self.refresh_all()
        self.status_var.set(f"Návrh #{self.selected_approval_id} byl zamítnut")

    def sync_once(self) -> None:
        self.sync_button.configure(state="disabled")
        self._set_sync_progress("Spoustim synchronizaci...", None, None)
        self.status_var.set("Synchronizace probiha...")

        def worker() -> None:
            try:
                result = self.agent_service.run_cycle(progress_callback=self._queue_sync_progress)
                message = (
                    f"Synchronizace dokoncena | e-maily={result.checked_emails} "
                    f"schvaleni={result.pending_approvals}"
                )
            except Exception as exc:
                message = f"Synchronizace selhala: {exc}"
            self.root.after(0, lambda: self._finish_sync(message))

        Thread(target=worker, daemon=True).start()

    def _finish_sync(self, message: str) -> None:
        self.refresh_all()
        self._reset_sync_progress()
        self.sync_button.configure(state="normal")
        self.status_var.set(message)

    def _queue_sync_progress(
        self,
        message: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        self.root.after(0, lambda: self._set_sync_progress(message, current, total))

    def _set_sync_progress(
        self,
        message: str,
        current: int | None,
        total: int | None,
    ) -> None:
        self.sync_progress_var.set(message)
        if current is not None and total is not None and total > 0:
            if str(self.sync_progress.cget("mode")) != "determinate":
                self.sync_progress.stop()
                self.sync_progress.configure(mode="determinate")
            self.sync_progress.configure(maximum=total, value=min(current, total))
            self.status_var.set(f"{message} {current}/{total}")
            return

        if str(self.sync_progress.cget("mode")) != "indeterminate":
            self.sync_progress.configure(mode="indeterminate")
            self.sync_progress.start(10)
        self.status_var.set(message)

    def _reset_sync_progress(self) -> None:
        self.sync_progress.stop()
        self.sync_progress.configure(mode="determinate", maximum=100, value=0)
        self.sync_progress_var.set("")

    def _set_text(self, frame: ttk.Frame, value: str) -> None:
        text = frame.text_widget  # type: ignore[attr-defined]
        text.configure(state="normal")
        text.delete("1.0", END)
        text.insert("1.0", value)
        text.configure(state="disabled")

    def _show_agent_proposal(self, email_id: str) -> None:
        related_items = [
            item
            for item in self.approval_items
            if item.source_email_id == email_id
        ]
        if not related_items:
            self._set_text(
                self.email_proposal,
                "Agent pro tento e-mail zatím nevytvořil žádný návrh.",
            )
            self.selected_approval_id = None
            return

        pending_item = next(
            (item for item in related_items if item.status == "pending"),
            related_items[0],
        )
        self.selected_approval_id = pending_item.id

        blocks: list[str] = []
        for item in related_items:
            blocks.append(self._format_proposal_item(item))

        self._set_text(self.email_proposal, ("\n\n" + ("-" * 60) + "\n\n").join(blocks))

    def _extract_item_due_value(self, payload: dict[str, object]) -> str:
        for key in ("due_date", "starts_at", "ends_at"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return self._format_datetime_value(value.strip())
        return "-"

    def _format_proposal_item(self, item: ApprovalItemModel) -> str:
        payload = item.payload
        lines = [
            f"Akce: {self._format_action_type(item.action_type)}",
            f"Stav: {self._format_status(item.status)}",
            f"Nazev: {item.title}",
            f"Duvod: {item.reason or '-'}",
        ]

        summary = payload.get("summary") or payload.get("description")
        if isinstance(summary, str) and summary.strip():
            lines.append(f"Shrnuti: {summary.strip()}")

        due_value = self._extract_item_due_value(payload)
        if due_value != "-":
            lines.append(f"Termin: {due_value}")

        draft_reply = payload.get("draft_reply")
        if isinstance(draft_reply, str) and draft_reply.strip():
            lines.append("")
            lines.append("Navrh odpovedi:")
            lines.append(draft_reply.strip())

        suggested_actions = payload.get("suggested_actions")
        if isinstance(suggested_actions, list):
            normalized = [item for item in suggested_actions if isinstance(item, str) and item.strip()]
            if normalized:
                lines.append("")
                lines.append("Dalsi kroky:")
                lines.extend(f"- {entry.strip()}" for entry in normalized)

        return "\n".join(lines)

    def _get_selected_email_entity(self) -> Email | None:
        if not self.selected_email_id:
            return None
        return self._email_entity_from_id(self.selected_email_id)

    def _get_today_email_entity(self) -> Email | None:
        if not self.selected_today_item or not self.selected_today_item.startswith("email:"):
            return None
        return self._email_entity_from_id(self.selected_today_item.split(":", 1)[1])

    def _get_today_task_id(self) -> int | None:
        if not self.selected_today_item or not self.selected_today_item.startswith("task:"):
            return None
        try:
            return int(self.selected_today_item.split(":", 1)[1])
        except ValueError:
            return None

    def _email_row_tags(self, email: EmailModel) -> tuple[str, ...]:
        if email.status == "confirmed":
            return ("completed",)
        if self._email_has_pending_action(email.id) or email.category in {
            "uncategorized",
            "task",
            "new_order",
            "calendar",
            "invoice",
        }:
            return ("attention",)
        return ()

    def _email_has_pending_action(self, email_id: str) -> bool:
        return any(
            item.status == "pending" and item.source_email_id == email_id
            for item in self.approval_items
        )

    def _email_entity_from_id(self, email_id: str) -> Email | None:
        email = crud.get_email(self.config, email_id)
        if email is None:
            return None
        return Email(
            id=email.id,
            thread_id=email.thread_id,
            sender=email.sender,
            subject=email.subject,
            body=email.body,
            received_at=email.received_at,
            attachments=list(email.attachments),
            category=email.category,
            priority=email.priority,
            project_id=email.project_id,
        )

    def _display_email_body(self, body: str) -> str:
        normalized = body or ""
        if "<" in normalized and ">" in normalized:
            normalized = html_to_text(normalized)
        return cleanup_email_text(normalized) or "-"

    def _format_action_type(self, action_type: str) -> str:
        labels = {
            "create_task": "Na ukol",
            "create_invoice": "Na fakturu",
            "create_calendar_event": "Do kalendare",
            "draft_email_reply": "Navrhnout odpoved",
            "monitor_only": "Jen sledovat",
        }
        return labels.get(action_type, action_type)

    def _format_status(self, status: str) -> str:
        labels = {
            "pending": "Ceka",
            "approved": "Schvaleno",
            "rejected": "Zamitnuto",
            "processed": "Zpracovano",
            "confirmed": "Potvrzeno",
            "archived": "Archivovano",
            "done": "Hotovo",
            "active": "Aktivni",
            "new": "Nova",
            "in_progress": "Rozpracovana",
            "waiting": "Cekajici",
        }
        return labels.get(status, status)

    def _format_priority(self, priority: str) -> str:
        labels = {
            "high": "Vysoka",
            "normal": "Normalni",
            "low": "Nizka",
        }
        return labels.get(priority, priority)

    def _format_category(self, category: str) -> str:
        labels = {
            "invoice": "Faktura",
            "calendar": "Kalendar",
            "new_order": "Zakazka",
            "task": "Ukol",
            "newsletter": "Newsletter",
            "marketing": "Marketing",
            "notification": "Notifikace",
            "banking": "Banka",
            "general": "Jen evidovat",
            "uncategorized": "Neroztridene",
        }
        return labels.get(category, category)

    def _project_status_label(self, status: str) -> str:
        labels = {
            "new": "Nova",
            "in_progress": "Rozpracovana",
            "waiting": "Cekajici",
            "done": "Hotova",
            "active": "Rozpracovana",
        }
        return labels.get(status, "Nova")

    def _project_status_value(self, label: str) -> str:
        values = {
            "Nova": "new",
            "Rozpracovana": "in_progress",
            "Cekajici": "waiting",
            "Hotova": "done",
        }
        return values.get(label, "new")

    def _project_name(self, project_id: int | None) -> str:
        if project_id is None:
            return "-"
        project = next((item for item in self.project_items if item.id == project_id), None)
        return project.name if project is not None else f"#{project_id}"

    def _format_related_type(self, related_type: str) -> str:
        labels = {
            "invoice": "Faktura",
            "task": "Ukol",
            "email": "E-mail",
            "calendar_event": "Kalendar",
        }
        return labels.get(related_type, related_type or "-")

    def _is_today_relevant_task(self, task: TaskModel) -> bool:
        return task.status in {"pending", "done"} and self._is_due_today(task.due_date)

    def _is_today_relevant_invoice(self, invoice: InvoiceModel) -> bool:
        return invoice.status == "pending"

    def _is_today_relevant_reminder(self, reminder: ReminderModel) -> bool:
        return reminder.status == "pending"

    def _is_received_today(self, value: str) -> bool:
        if not value:
            return False
        try:
            dt_value = datetime.fromisoformat(value.strip())
        except ValueError:
            return False
        if dt_value.tzinfo is not None:
            dt_value = dt_value.astimezone()
        return dt_value.date() == datetime.now().astimezone().date()

    def _is_due_today(self, value: str | None) -> bool:
        if not value:
            return False

        normalized = value.strip()
        if not normalized:
            return False

        try:
            dt_value = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                dt_value = datetime.fromisoformat(f"{normalized}T00:00:00")
            except ValueError:
                return False

        if dt_value.tzinfo is not None:
            dt_value = dt_value.astimezone()
        return dt_value.date() == datetime.now().astimezone().date()

    def _format_datetime_value(self, value: str | None) -> str:
        if not value:
            return "-"

        normalized = value.strip()
        if not normalized:
            return "-"

        try:
            dt_value = datetime.fromisoformat(normalized)
            if dt_value.tzinfo is not None:
                dt_value = dt_value.astimezone()
            if dt_value.hour == 0 and dt_value.minute == 0 and "T" not in normalized:
                return f"{dt_value.day}.{dt_value.month}.{dt_value.year}"
            return (
                f"{dt_value.day}.{dt_value.month}.{dt_value.year} "
                f"{dt_value.hour:02d}:{dt_value.minute:02d}"
            )
        except ValueError:
            pass

        try:
            dt_value = datetime.fromisoformat(f"{normalized}T00:00:00")
            return f"{dt_value.day}.{dt_value.month}.{dt_value.year}"
        except ValueError:
            return normalized

    def _format_invoice_detail(self, invoice: InvoiceModel) -> str:
        source_email = crud.get_email(self.config, invoice.source_email_id) if invoice.source_email_id else None
        source_email_block = ""
        if source_email is not None:
            source_email_block = (
                "\n\nPuvodni e-mail:\n"
                f"Predmet: {source_email.subject}\n"
                f"Odesilatel: {source_email.sender}\n"
                f"Prijato: {self._format_datetime_value(source_email.received_at)}\n"
                f"Shrnuti: {source_email.summary or '-'}\n\n"
                f"Telo zpravy:\n{self._display_email_body(source_email.body)}"
            )

        return (
            f"ID: {invoice.id}\n"
            f"Dodavatel: {invoice.supplier}\n"
            f"Cislo faktury: {invoice.invoice_number or '-'}\n"
            f"Celkova castka: {invoice.amount if invoice.amount is not None else '-'} {invoice.currency}\n"
            f"Splatnost: {self._format_datetime_value(invoice.due_date)}\n"
            f"Stav: {self._format_status(invoice.status)}\n"
            f"Zakazka: {self._project_name(invoice.project_id)}\n"
            f"Zdrojovy e-mail: {invoice.source_email_id or '-'}\n"
            f"PDF priloha: {invoice.attachment_path or '-'}"
            f"{source_email_block}"
        )

    def _format_task_detail(self, task: TaskModel) -> str:
        return (
            f"ID: {task.id}\n"
            f"Nazev: {task.title}\n"
            f"Priorita: {self._format_priority(task.priority)}\n"
            f"Stav: {self._format_status(task.status)}\n"
            f"Termin: {self._format_datetime_value(task.due_date)}\n"
            f"Zakazka: {self._project_name(task.project_id)}\n"
            f"Zdrojovy e-mail: {task.source_email_id or '-'}\n\n"
            f"Popis:\n{task.description or '-'}"
        )

    def _filter_emails(self, emails: list[EmailModel]) -> list[EmailModel]:
        selected_filter = self.email_filter_var.get()
        archived_emails = [email for email in emails if email.status == "archived"]
        active_emails = [email for email in emails if email.status != "archived"]
        work_categories = {"uncategorized", "task", "new_order", "calendar", "invoice"}

        if selected_filter == "Archiv":
            return archived_emails
        if selected_filter == "Vse":
            return active_emails
        if selected_filter == "Newslettery":
            return [email for email in active_emails if email.category == "newsletter"]
        if selected_filter == "Neroztridene":
            return [email for email in active_emails if email.category == "uncategorized"]

        return [
            email
            for email in active_emails
            if email.category in work_categories
            or any(
                item.status == "pending" and item.source_email_id == email.id
                for item in self.approval_items
            )
        ]

    def _build_archive_tab(self) -> None:
        self.archive_tab.columnconfigure(0, weight=1)
        self.archive_tab.columnconfigure(1, weight=2)
        self.archive_tab.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(
            self.archive_tab,
            text="Archiv",
            padding=8,
            style="Card.TLabelframe",
        )
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.archive_tree = ttk.Treeview(
            list_frame,
            columns=("kind", "title", "date"),
            show="headings",
        )
        for column, width in (("kind", 90), ("title", 360), ("date", 160)):
            header_text = {"kind": "Typ", "title": "Nazev", "date": "Datum"}[column]
            self.archive_tree.heading(column, text=header_text)
            self.archive_tree.column(column, width=width, anchor="w")
        self.archive_tree.grid(row=0, column=0, sticky="nsew")
        self.archive_tree.bind("<<TreeviewSelect>>", self._on_archive_selected)
        archive_scroll = ttk.Scrollbar(
            list_frame,
            orient=VERTICAL,
            command=self.archive_tree.yview,
        )
        archive_scroll.grid(row=0, column=1, sticky="ns")
        self.archive_tree.configure(yscrollcommand=archive_scroll.set)

        detail_frame = ttk.LabelFrame(
            self.archive_tab,
            text="Detail archivovane polozky",
            padding=8,
            style="Card.TLabelframe",
        )
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.archive_detail = self._create_text(detail_frame)
        self.archive_detail.grid(row=0, column=0, sticky="nsew")

    def _refresh_archive(self, emails: list[EmailModel], tasks: list[TaskModel]) -> None:
        for item_id in self.archive_tree.get_children():
            self.archive_tree.delete(item_id)

        for email in emails:
            if email.status != "archived":
                continue
            self.archive_tree.insert(
                "",
                END,
                iid=f"email:{email.id}",
                values=("E-mail", email.subject, self._format_datetime_value(email.received_at)),
            )

        for task in tasks:
            if task.status != "archived":
                continue
            self.archive_tree.insert(
                "",
                END,
                iid=f"task:{task.id}",
                values=(
                    "Ukol",
                    task.title,
                    self._format_datetime_value(task.completed_at or task.created_at),
                ),
            )

        if self.selected_archive_item and self.archive_tree.exists(self.selected_archive_item):
            self.archive_tree.selection_set(self.selected_archive_item)
            self.archive_tree.focus(self.selected_archive_item)
            self._show_archive_detail(self.selected_archive_item)
        elif self.archive_tree.get_children():
            first_id = str(self.archive_tree.get_children()[0])
            self.selected_archive_item = first_id
            self.archive_tree.selection_set(first_id)
            self.archive_tree.focus(first_id)
            self._show_archive_detail(first_id)
        else:
            self.selected_archive_item = None
            self._set_text(self.archive_detail, "Archiv je zatim prazdny.")

    def _on_archive_selected(self, event: object) -> None:
        selection = self.archive_tree.selection()
        if not selection:
            return
        self.selected_archive_item = str(selection[0])
        self._show_archive_detail(self.selected_archive_item)

    def _show_archive_detail(self, item_key: str) -> None:
        item_type, _, raw_id = item_key.partition(":")
        if item_type == "email":
            email = crud.get_email(self.config, raw_id)
            if email is None:
                self._set_text(self.archive_detail, "E-mail nebyl nalezen.")
                return
            detail = (
                f"Typ: E-mail\n"
                f"Predmet: {email.subject}\n"
                f"Odesilatel: {email.sender}\n"
                f"Prijato: {self._format_datetime_value(email.received_at)}\n"
                f"Kategorie: {self._format_category(email.category)}\n"
                f"Stav: {self._format_status(email.status)}\n\n"
                f"Text:\n{self._display_email_body(email.body)}"
            )
            self.current_source_email_id = email.id
            self._set_text(self.archive_detail, detail)
            return

        if item_type == "task":
            try:
                task_id = int(raw_id)
            except ValueError:
                self._set_text(self.archive_detail, "Ukol nebyl nalezen.")
                return
            task = next((item for item in self.task_items if item.id == task_id), None)
            if task is None:
                self._set_text(self.archive_detail, "Ukol nebyl nalezen.")
                return
            self.current_source_email_id = task.source_email_id
            self._set_text(self.archive_detail, self._format_task_detail(task))
            return

        self._set_text(self.archive_detail, "Polozka nebyla nalezena.")

    def archive_selected_emails(self) -> None:
        selected_ids = list(self.email_tree.selection())
        if not selected_ids and self.selected_email_id:
            selected_ids = [self.selected_email_id]
        if not selected_ids:
            messagebox.showinfo("E-maily", "Nejprve vyber e-mail.")
            return
        for email_id in selected_ids:
            crud.update_email_status(self.config, str(email_id), "archived")
        self.refresh_all()
        self.status_var.set(f"Archivovano e-mailu: {len(selected_ids)}")

    def archive_selected_tasks(self) -> None:
        selected_ids = [int(item_id) for item_id in self.task_tree.selection()]
        if not selected_ids and self.selected_task_id is not None:
            selected_ids = [self.selected_task_id]
        if not selected_ids:
            messagebox.showinfo("Ukoly", "Nejprve vyber ukol.")
            return
        for task_id in selected_ids:
            self.task_service.archive_task(task_id)
        self.refresh_all()
        self.status_var.set(f"Archivovano ukolu: {len(selected_ids)}")

    def today_archive_selected(self) -> None:
        selection = list(self.today_tree.selection())
        if not selection and self.selected_today_item:
            selection = [self.selected_today_item]
        if not selection:
            messagebox.showinfo("Nezpracovane", "Nejprve vyber polozku.")
            return

        archived_count = 0
        for item_key in selection:
            item_type, _, raw_id = str(item_key).partition(":")
            if item_type == "email":
                if crud.update_email_status(self.config, raw_id, "archived"):
                    archived_count += 1
            elif item_type == "task":
                try:
                    task_id = int(raw_id)
                except ValueError:
                    continue
                if self.task_service.archive_task(task_id):
                    archived_count += 1

        self.refresh_all()
        self.status_var.set(f"Archivovano polozek: {archived_count}")


def run_desktop_app(config: AppConfig | None = None) -> None:
    DesktopApp(config).run()

