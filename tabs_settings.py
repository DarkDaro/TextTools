"""Вкладка «Настройки»: пути к внешним скриптам, общие параметры.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG, CONFIG_FILE
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         BigButton, Tooltip, FONT_SMALL)
from wrappers import DEFAULTS


class SettingsTab(ctk.CTkFrame):
    LABEL = "Настройки"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Здесь настраиваются пути к внешним скриптам (обычно менять не нужно — "
            "уже стоят правильные) и хранилище по умолчанию. "
            "Все настройки сохраняются автоматически."))

        s1 = Section(parent, "Пути к внешним скриптам")
        for label, key in (("emoji-cleaner:", "emoji_cleaner"),
                           ("clean_text_files:", "clean_text"),
                           ("md_replace:", "md_replace"),
                           ("char_search:", "char_search"),
                           ("refile:", "refile")):
            PathField(s1.inner, label, f"script_{key}", CFG, file_mode="file",
                      tooltip=f"Путь к скрипту. По умолчанию: {DEFAULTS[key]}")

        s2 = Section(parent, "Общее")
        PathField(s2.inner, "Vault по умолчанию:", "default_vault", CFG, file_mode="dir",
                  tooltip="Подставляется в поля хранилища на других вкладках, "
                          "если они пустые.")
        CheckField(s2.inner, "Показывать команды в логе", "show_cmd", CFG, default=True,
                   tooltip="Показывать в окне вывода командную строку перед результатом."
                   ).pack(anchor="w")

        # --- Сохранение / сброс ---
        s3 = Section(parent, "Сохранение настроек")
        ctk.CTkLabel(s3.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Все настройки сохраняются автоматически при каждом изменении "
            "(путь, галочка, тема). Кнопки ниже — для ручного управления."
        )).pack(anchor="w", pady=(0, 4))
        r3 = ctk.CTkFrame(s3.inner, fg_color="transparent")
        r3.pack(fill="x", pady=2)
        BigButton(r3, "Сохранить сейчас", self._save_now,
                  tooltip="Принудительно записать все текущие значения в gui_config.json."
                  ).pack(side="left", padx=(0, 8))
        b_open = ctk.CTkButton(r3, text="Открыть конфиг", height=34,
                               command=self._open_config)
        b_open.pack(side="left", padx=8)
        Tooltip(b_open, "Открыть файл настроек в Блокноте. "
                        "Можно править вручную; изменения подхватятся после перезапуска.")
        b_reset = ctk.CTkButton(r3, text="Сбросить всё", height=34,
                                command=self._reset_all)
        b_reset.pack(side="left", padx=8)
        Tooltip(b_reset, "Очистить все сохранённые настройки (пути, галочки, тема). "
                         "Окно можно закрыть и открыть заново — поля будут пустыми.")

        s4 = Section(parent, "Информация")
        ctk.CTkLabel(s4.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            f"Настройки хранятся в: {CONFIG_FILE}\n"
            "Отчёты сохраняются в: reports/ (рядом с программой)\n\n"
            "Безопасность:\n"
            "  • Всё, что меняет файлы, по умолчанию в dry-run (только отчёт)\n"
            "  • Реальная запись — только явный чекбокс «Применить изменения»\n"
            "  • Бэкапы: .bak рядом с файлами или md_replace_backups в хранилище\n"
            "  • Кнопка «Стоп» внизу окна прерывает запущенную операцию"
        )).pack(anchor="w")

    def _log(self, msg, tag=None):
        from gui_ctk import _app
        _app.log_line(msg, tag)

    def _save_now(self):
        from gui_config import _load, CONFIG_FILE
        import json
        try:
            CONFIG_FILE.write_text(
                json.dumps(_load(), ensure_ascii=False, indent=2),
                encoding="utf-8")
            self._log("Настройки сохранены: ", "ok")
            self._log(f"{CONFIG_FILE}\n")
        except Exception as e:
            self._log(f"Ошибка сохранения: {e}\n", "err")

    def _open_config(self):
        import subprocess
        subprocess.Popen(["notepad.exe", str(CONFIG_FILE)])

    def _reset_all(self):
        from gui_config import CONFIG_FILE
        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink()
            except Exception as e:
                self._log(f"Ошибка сброса: {e}\n", "err")
                return
        self._log("Настройки сброшены. Перезапустите программу.\n", "ok")