"""Tkinter-based desktop wrapper that reuses the downloader core."""
from __future__ import annotations

import asyncio
import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import Iterable

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .telethon_client import TelethonClientManager

from .cli import parse_datetime_option, run_download
from .config import AppConfig, build_app_config
from .logging_config import configure_logging

LOGGER = logging.getLogger(__name__)
MEDIA_TYPES = ["photo", "video", "document", "voice", "audio", "sticker", "gif", "other"]
LOG_QUEUE: queue.Queue[str] = queue.Queue()


async def _send_code_request(config: AppConfig, phone: str) -> str:
    client = TelegramClient(config.session_name, config.api_id, config.api_hash)
    await client.connect()
    try:
        result = await client.send_code_request(phone)
        return result.phone_code_hash
    finally:
        await client.disconnect()


async def _sign_in(
    config: AppConfig,
    phone: str,
    code: str,
    phone_code_hash: str,
    password: str | None,
) -> None:
    client = TelegramClient(config.session_name, config.api_id, config.api_hash)
    await client.connect()
    try:
        await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=phone_code_hash,
            password=password or None,
        )
    finally:
        await client.disconnect()


async def _check_authorized(config: AppConfig) -> bool:
    try:
        async with TelethonClientManager(config) as _:
            return True
    except RuntimeError as exc:
        if "not authorized" in str(exc).lower():
            return False
        raise


class QueueLogHandler(logging.Handler):
    """Log handler that writes formatted entries to a queue for the GUI."""

    def __init__(self, output_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.output_queue = output_queue
        self.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.output_queue.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)


def _ensure_logging() -> None:
    configure_logging("INFO", Path("logs"))
    handler = QueueLogHandler(LOG_QUEUE)
    logging.getLogger().addHandler(handler)


def _browse_folder(entry: ttk.Entry) -> None:
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)


def _build_media_selection(frame: ttk.Frame) -> dict[str, tk.BooleanVar]:
    vars: dict[str, tk.BooleanVar] = {}
    for mt in MEDIA_TYPES:
        var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(frame, text=mt.capitalize(), variable=var)
        chk.pack(anchor="w", pady=1)
        vars[mt] = var
    return vars


def _append_log(text_widget: scrolledtext.ScrolledText) -> None:
    while not LOG_QUEUE.empty():
        line = LOG_QUEUE.get_nowait()
        text_widget.configure(state="normal")
        text_widget.insert(tk.END, line + "\n")
        text_widget.see(tk.END)
        text_widget.configure(state="disabled")


def _enable_context_menu(entry: tk.Entry) -> None:
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label="Cut", command=lambda: entry.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: entry.event_generate("<<Paste>>"))

    def _show_menu(event: tk.Event) -> None:
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    entry.bind("<Button-3>", _show_menu)


def _execute_login_dialog(root: tk.Tk, config: AppConfig) -> bool:
    result = {"success": False, "phone_code_hash": None}

    def _close(window: tk.Toplevel) -> None:
        window.grab_release()
        window.destroy()

    login_window = tk.Toplevel(root)
    login_window.title("Telegram login")
    login_window.grab_set()

    ttk.Label(login_window, text="Phone number:").grid(row=0, column=0, sticky="w", pady=4, padx=4)
    phone_entry = ttk.Entry(login_window, width=40)
    phone_entry.insert(0, config.phone_number or "")
    phone_entry.grid(row=0, column=1, pady=4, padx=4)

    ttk.Label(login_window, text="Code:").grid(row=1, column=0, sticky="w", pady=4, padx=4)
    code_entry = ttk.Entry(login_window, width=40)
    code_entry.grid(row=1, column=1, pady=4, padx=4)

    ttk.Label(login_window, text="2FA password (if needed):").grid(
        row=2, column=0, sticky="w", pady=4, padx=4
    )
    password_entry = ttk.Entry(login_window, width=40, show="*")
    password_entry.grid(row=2, column=1, pady=4, padx=4)

    status_label = ttk.Label(login_window, text="Send code to your phone.", foreground="gray")
    status_label.grid(row=3, column=0, columnspan=2, pady=6)

    def _send_code() -> None:
        phone = phone_entry.get().strip()
        if not phone:
            status_label.configure(text="Provide a phone number first.", foreground="red")
            return
        try:
            code_hash = asyncio.run(_send_code_request(config, phone))
            result["phone_code_hash"] = code_hash
            status_label.configure(text="Code sent. Enter the code below.", foreground="green")
        except Exception as exc:
            LOGGER.exception("Unable to send code: %s", exc)
            status_label.configure(text="Failed to send code. See logs.", foreground="red")

    def _submit() -> None:
        phone = phone_entry.get().strip()
        code = code_entry.get().strip()
        password = password_entry.get().strip() or None
        code_hash = result["phone_code_hash"]
        if not phone or not code or not code_hash:
            status_label.configure(text="Phone, code, and sent hash required.", foreground="red")
            return
        try:
            asyncio.run(_sign_in(config, phone, code, code_hash, password))
            result["success"] = True
            _close(login_window)
        except SessionPasswordNeededError:
            status_label.configure(text="2FA password required.", foreground="orange")
        except Exception as exc:
            LOGGER.exception("Sign-in failed: %s", exc)
            status_label.configure(text="Sign-in failed. See logs.", foreground="red")

    ttk.Button(login_window, text="Send code", command=_send_code).grid(row=4, column=0, pady=8, padx=4)
    ttk.Button(login_window, text="Submit", command=_submit).grid(row=4, column=1, pady=8, padx=4)

    login_window.protocol("WM_DELETE_WINDOW", lambda: _close(login_window))
    login_window.wait_window()
    return result["success"]


def start_gui() -> None:
    _ensure_logging()
    root = tk.Tk()
    root.title("Telegram Media Loader")
    root.geometry("780x520")

    main_frame = ttk.Frame(root, padding=12)
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="Chat URL:").grid(row=0, column=0, sticky="w")
    chat_entry = ttk.Entry(main_frame, width=70)
    _enable_context_menu(chat_entry)
    chat_entry.grid(row=0, column=1, columnspan=2, pady=4, sticky="ew")

    ttk.Label(main_frame, text="Output Root:").grid(row=1, column=0, sticky="w")
    output_entry = ttk.Entry(main_frame, width=55)
    _enable_context_menu(output_entry)
    output_entry.insert(0, str(Path.cwd() / "downloads"))
    output_entry.grid(row=1, column=1, pady=4, sticky="ew")
    ttk.Button(main_frame, text="Browse…", command=lambda: _browse_folder(output_entry)).grid(
        row=1, column=2, padx=4
    )

    ttk.Label(main_frame, text="Date From (YYYY-MM-DD or YYYY-MM-DDTHH:MM):").grid(
        row=2, column=0, sticky="w"
    )
    date_from_entry = ttk.Entry(main_frame, width=25)
    _enable_context_menu(date_from_entry)
    date_from_entry.grid(row=2, column=1, pady=4, sticky="w")

    ttk.Label(main_frame, text="Date To (YYYY-MM-DD or YYYY-MM-DDTHH:MM):").grid(
        row=3, column=0, sticky="w"
    )
    date_to_entry = ttk.Entry(main_frame, width=25)
    _enable_context_menu(date_to_entry)
    date_to_entry.grid(row=3, column=1, pady=4, sticky="w")

    ttk.Label(main_frame, text="Media Types:").grid(row=4, column=0, sticky="nw")
    media_frame = ttk.Frame(main_frame)
    media_frame.grid(row=4, column=1, columnspan=2, pady=8, sticky="w")
    media_vars = _build_media_selection(media_frame)

    status_label = ttk.Label(main_frame, text="Idle", foreground="gray")
    status_label.grid(row=5, column=0, columnspan=3, pady=6, sticky="w")

    start_button = ttk.Button(main_frame, text="Start")
    start_button.grid(row=6, column=0, columnspan=1, pady=8, sticky="w")

    log_widget = scrolledtext.ScrolledText(main_frame, height=15, state="disabled", wrap="none")
    log_widget.grid(row=7, column=0, columnspan=3, pady=6, sticky="nsew")

    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(7, weight=1)

    download_thread: threading.Thread | None = None

    def _set_status(text: str, color: str = "black") -> None:
        status_label.configure(text=text, foreground=color)

    def _worker(
        config: AppConfig,
        chat_url: str,
        date_from: str,
        date_to: str,
        selected: Iterable[str],
    ) -> None:
        parsed_date_from = parse_datetime_option(date_from, config.tz)
        parsed_date_to = parse_datetime_option(date_to, config.tz)
        media_types = tuple(selected) if selected else config.default_media_types

        try:
            asyncio.run(
                run_download(
                    config=config,
                    chat_url=chat_url,
                    media_types=media_types,
                    date_from=parsed_date_from,
                    date_to=parsed_date_to,
                    progress=None,
                )
            )
            _set_status("Download finished", "green")
        except Exception as exc:
            LOGGER.exception("Download failed: %s", exc)
            _set_status("Download failed", "red")
        finally:
            start_button.configure(state="normal")

    def _on_start() -> None:
        nonlocal download_thread
        if download_thread and download_thread.is_alive():
            return

        chat_url = chat_entry.get().strip()
        output_root = output_entry.get().strip()
        if not chat_url or not output_root:
            LOGGER.error("Chat URL and output root are required.")
            return

        try:
            config_file = Path("config.yaml")
            config = build_app_config(
                config_path=config_file if config_file.exists() else None,
                cli_output_root=Path(output_root),
                cli_log_level=None,
            )
        except Exception as exc:
            LOGGER.exception("Configuration error: %s", exc)
            _set_status("Config error", "red")
            return

        try:
            authorized = asyncio.run(_check_authorized(config))
        except RuntimeError:
            authorized = False
        except Exception as exc:
            LOGGER.exception("Authorization check failed: %s", exc)
            _set_status("Auth check failed", "red")
            return

        if not authorized:
            _set_status("Login required", "orange")
            if not _execute_login_dialog(root, config):
                _set_status("Login canceled", "red")
                return
            try:
                authorized = asyncio.run(_check_authorized(config))
            except RuntimeError:
                authorized = False
            except Exception as exc:
                LOGGER.exception("Authorization check failed: %s", exc)
                _set_status("Auth check failed", "red")
                return
            if not authorized:
                _set_status("Login failed", "red")
                return

        selected_types = [mt for mt, var in media_vars.items() if var.get()]
        start_button.configure(state="disabled")
        _set_status("Downloading…", "blue")
        download_thread = threading.Thread(
            target=_worker,
            args=(config, chat_url, date_from_entry.get(), date_to_entry.get(), selected_types),
            daemon=True,
        )
        download_thread.start()

    start_button.configure(command=_on_start)

    def _poll_logs() -> None:
        _append_log(log_widget)
        root.after(200, _poll_logs)

    root.after(200, _poll_logs)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
