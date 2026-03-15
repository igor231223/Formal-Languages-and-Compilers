# Copilot / AI agent instructions — Formal-Languages-and-Compilers

Кратко: этот репозиторий — небольшое PyQt6 GUI-приложение (специализированный текстовый
редактор) с поддержкой локализации и сборкой через PyInstaller. Цель файла — дать точные указания
агентам (Copilot/ботам), чтобы быстро вносить правки и создавать полезные изменения.

- **Входные точки:** `editor_window.py` (основной UI, класс `EditorWindow`), `main.py` (минимальная
  точка входа). Запуск разработки: `python editor_window.py` или `python main.py`.
- **Зависимости / сборка:** `requirements.txt` (PyQt6, PyInstaller и пр.). Сборка exe — команда из
  `README.md` с `pyinstaller --onefile --windowed --add-data "icons;icons" --add-data "translations;translations" --name "TextEditor" editor_window.py`.

Ключевая архитектура и паттерны
- Однооконное приложение с двумя основными панелями: верхняя — `QTextEdit` (редактор), нижняя —
  `QTextEdit` (вывод). Логика UI сосредоточена в `EditorWindow`.
- Локализация: JSON-словари в `translations/{ru,en}.json`. Функция `load_translation()` читает
  JSON, ключи используются через `tr(key)`; полный перерасшифровщик GUI — `retranslate_ui()`.
  Если добавляете UI-строку — добавьте ключ в обе `translations/*.json` и обновите `retranslate_ui()`.
- Ресурсы при упаковке: используйте `resource_path(relative_path)` при обращении к `icons/` и `translations/`.
  Это обеспечивает корректную работу как из исходников, так и из собранного exe (sys._MEIPASS).
- UI-элементы: имена полей в `EditorWindow` следуют схеме `menu_*` и `tb_*` (toolbar). Добавление
  пункта меню — создать `QAction` в `create_actions()`, добавить в `create_menus()` и прописать текст
  в `retranslate_ui()` и `translations/*.json`.

Developer workflows (конкретные команды)
- Создать виртуальное окружение и установить зависимости:
  ```bash
  python -m venv venv
  venv\Scripts\activate   # Windows
  pip install -r requirements.txt
  ```
- Запуск в dev-режиме:
  ```bash
  python editor_window.py
  ```
- Быстрая сборка Windows exe (как в README):
  ```bash
  pip install pyinstaller
  pyinstaller --onefile --windowed --add-data "icons;icons" --add-data "translations;translations" --name "TextEditor" editor_window.py
  # результат: dist\TextEditor.exe
  ```

Project-specific conventions (важно для изменений)
- Не редактируйте прямые пути к иконкам/переводам — всегда используйте `resource_path()`.
- UI-текст должен управляться через ключи переводов и `retranslate_ui()` — это позволяет менять
  язык без перезапуска.
- Состояние «несохранено» хранится в `self.is_dirty`; методы `maybe_save()`, `save_file()` и
  `save_as_file()` управляют подтверждениями — при добавлении операций сохранения проверяйте
  взаимодействие с этими методами.

Debug / тестирование / отладка
- Если интерфейс не загружается корректно, запустите `python editor_window.py` в консоли —
  ошибки при загрузке переводов печатаются в stdout (см. обработку исключений в `load_translation`).
- Для проверки перевода: отредактируйте `translations/ru.json` и переключитесь в интерфейсе
  (меню "Язык") — `retranslate_ui()` пересоздаст меню и тулбар.

Интеграционные точки
- PyInstaller: `--add-data` нужен для `icons` и `translations` (см. README). В `build/` уже есть
  артефакты сборки (если нужно исследовать). Есть файл `TextEditor.spec` в корне — можно
  модифицировать для тонкой настройки сборки.

Что не менять без согласования
- Глобальную структуру `EditorWindow` (инициализация UI, разделение на `create_actions/create_menus/create_toolbar`),
  и схему переводов — изменения должны быть совместимы с retranslate_ui.

Примеры быстрых правок (шабоны)
- Добавить пункт меню "Export":
  1) В `create_actions()` — `self.menu_export = QAction(self)` + подключение к слоту.
  2) В `create_menus()` — `file_menu.addAction(self.menu_export)`.
  3) В `retranslate_ui()` — `self.menu_export.setText(self.tr("file_export"))`.
  4) Добавить `"file_export": "Export"` и русскую строку в `translations/*.json`.

Если что-то не понятно или нужно больше деталей (например: где именно добавить тесты,
или как подготовить CI для сборки exe), напишите — скорректирую инструкцию.
