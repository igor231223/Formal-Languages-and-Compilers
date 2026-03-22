import os
import sys
import json

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QKeySequence, QAction, QIcon, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QTextEdit,
    QFileDialog, QMessageBox, QToolBar, QApplication, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QLabel
)

from scanner import Scanner
from parser import analyze_syntax

class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.is_dirty = False
        self.current_lang = "ru"
        self.trans = {}

        self.setMinimumHeight(500)
        self.setMinimumWidth(700)
        self.setWindowIcon(QIcon(resource_path("icons/logo.svg")))

        self.setGeometry(200, 100, 1100, 750)

        self.init_ui()
        self.create_actions()

        self.load_translation(self.current_lang)

        self.editor.textChanged.connect(self.on_text_changed)
        self.output_table.cellClicked.connect(self.go_to_error)
        
        self.editor.cursorPositionChanged.connect(self.update_cursor_status)

        self.update_cursor_status()



    def load_translation(self, lang_code: str):
        path = resource_path(os.path.join("translations", f"{lang_code}.json"))
        try:
            with open(path, encoding="utf-8") as f:
                self.trans = json.load(f)
        except Exception as e:
            print(f"Translation load error ({lang_code}): {e}")
            self.trans = {}

        self.current_lang = lang_code
        self.retranslate_ui()

    def tr(self, key: str) -> str:
        return self.trans.get(key, key)

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("app_title"))

        # Text for menu
        self.menu_new.setText(self.tr("file_new"))
        self.menu_open.setText(self.tr("file_open"))
        self.menu_save.setText(self.tr("file_save"))
        self.menu_save_as.setText(self.tr("file_save_as"))
        self.menu_exit.setText(self.tr("file_exit"))

        self.menu_undo.setText(self.tr("edit_undo"))
        self.menu_redo.setText(self.tr("edit_redo"))
        self.menu_cut.setText(self.tr("edit_cut"))
        self.menu_copy.setText(self.tr("edit_copy"))
        self.menu_paste.setText(self.tr("edit_paste"))
        self.menu_select_all.setText(self.tr("edit_select_all"))

        self.menu_run.setText(self.tr("run"))

        self.lang_ru_act.setText(self.tr("lang_ru"))
        self.lang_en_act.setText(self.tr("lang_en"))

        self.help_act.setText(self.tr("help_help"))
        self.about_act.setText(self.tr("help_about"))

        # Text for tooltips
        self.tb_about.setToolTip(self.tr("about_title"))
        self.tb_help.setToolTip(self.tr("help_help"))
        self.tb_paste.setToolTip(self.tr("edit_paste"))
        self.tb_copy.setToolTip(self.tr("edit_copy"))
        self.tb_cut.setToolTip(self.tr("edit_cut"))
        self.tb_redo.setToolTip(self.tr("edit_redo"))
        self.tb_undo.setToolTip(self.tr("edit_undo"))
        self.tb_save.setToolTip(self.tr("file_save"))
        self.tb_open.setToolTip(self.tr("file_open"))
        self.tb_new.setToolTip(self.tr("file_new"))
        self.tb_run.setToolTip(self.tr("run"))

        # Recreate menu + toolbar
        self.menuBar().clear()
        self.create_menus()

        for toolbar in self.findChildren(QToolBar):
            self.removeToolBar(toolbar)
        self.create_toolbar()

        self.output_table.setHorizontalHeaderLabels([
            self.tr("table_err_fragment"),
            self.tr("table_err_location"),
            self.tr("table_err_desc"),
        ])

        self.update_cursor_status()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.splitter)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(" "))
        self.splitter.addWidget(self.editor)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)

        self.output_table = QTableWidget()
        self.output_table.setColumnCount(3)
        self.output_table.setHorizontalHeaderLabels(
            ["Фрагмент", "Местоположение", "Описание"]
        )
        self.output_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.output_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.output_table.verticalHeader().setVisible(False)
        self.output_table.horizontalHeader().setStretchLastSection(True)
        self.output_table.setFont(QFont("Consolas", 11))

        self.output_panel = QWidget()
        output_layout = QVBoxLayout(self.output_panel)
        output_layout.setContentsMargins(4, 4, 4, 4)
        self.analysis_result_label = QLabel()
        self.analysis_result_label.setWordWrap(True)
        output_layout.addWidget(self.analysis_result_label)
        output_layout.addWidget(self.output_table)
        self.splitter.addWidget(self.output_panel)

        self.splitter.setSizes([550, 200])

    def create_actions(self):
        # Menu actions
        # File
        self.menu_new = QAction(self)
        self.menu_new.setShortcut(QKeySequence("Ctrl+N"))
        self.menu_new.triggered.connect(self.new_file)

        self.menu_open = QAction(self)
        self.menu_open.setShortcut(QKeySequence("Ctrl+O"))
        self.menu_open.triggered.connect(self.open_file)

        self.menu_save = QAction(self)
        self.menu_save.setShortcut(QKeySequence("Ctrl+S"))
        self.menu_save.triggered.connect(self.save_file)

        self.menu_save_as = QAction(self)
        self.menu_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.menu_save_as.triggered.connect(self.save_as_file)

        self.menu_exit = QAction(self)
        self.menu_exit.setShortcut(QKeySequence("Alt+F4"))
        self.menu_exit.triggered.connect(self.close)

        self.menu_undo = QAction(self)
        self.menu_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.menu_undo.triggered.connect(self.editor.undo)

        self.menu_redo = QAction(self)
        self.menu_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.menu_redo.triggered.connect(self.editor.redo)

        self.menu_cut = QAction(self)
        self.menu_cut.setShortcut(QKeySequence("Ctrl+X"))
        self.menu_cut.triggered.connect(self.editor.cut)

        self.menu_copy = QAction(self)
        self.menu_copy.setShortcut(QKeySequence("Ctrl+C"))
        self.menu_copy.triggered.connect(self.editor.copy)

        self.menu_paste = QAction(self)
        self.menu_paste.setShortcut(QKeySequence("Ctrl+V"))
        self.menu_paste.triggered.connect(self.editor.paste)

        self.menu_select_all = QAction(self)
        self.menu_select_all.setShortcut(QKeySequence("Ctrl+A"))
        self.menu_select_all.triggered.connect(self.editor.selectAll)

        # Run
        self.menu_run = QAction(self)
        self.menu_run.setShortcut(QKeySequence("F5"))
        self.menu_run.triggered.connect(self.run_analysis)

        # Language
        self.lang_ru_act = QAction(self)
        self.lang_ru_act.setCheckable(True)
        self.lang_ru_act.setChecked(True)
        self.lang_ru_act.triggered.connect(lambda: self.switch_language("ru"))

        self.lang_en_act = QAction(self)
        self.lang_en_act.setCheckable(True)
        self.lang_en_act.triggered.connect(lambda: self.switch_language("en"))

        # Help
        self.help_act = QAction(self)
        self.help_act.setShortcut(QKeySequence("F1"))
        self.help_act.triggered.connect(self.show_help)

        self.about_act = QAction(self)
        self.about_act.triggered.connect(self.show_about)

        # Toolbar actions
        self.tb_run = QAction(self)
        self.tb_run.setIcon(QIcon(resource_path("icons/run.svg")))
        self.tb_run.triggered.connect(self.run_analysis)

        self.tb_new = QAction(self)
        self.tb_new.setIcon(QIcon(resource_path("icons/new.svg")))
        self.tb_new.triggered.connect(self.new_file)

        self.tb_open = QAction(self)
        self.tb_open.setIcon(QIcon(resource_path("icons/open.svg")))
        self.tb_open.triggered.connect(self.open_file)

        self.tb_save = QAction(self)
        self.tb_save.setIcon(QIcon(resource_path("icons/save.svg")))
        self.tb_save.triggered.connect(self.save_file)

        self.tb_undo = QAction(self)
        self.tb_undo.setIcon(QIcon(resource_path("icons/undo.svg")))
        self.tb_undo.triggered.connect(self.editor.undo)

        self.tb_redo = QAction(self)
        self.tb_redo.setIcon(QIcon(resource_path("icons/redo.svg")))
        self.tb_redo.triggered.connect(self.editor.redo)

        self.tb_cut = QAction(self)
        self.tb_cut.setIcon(QIcon(resource_path("icons/cut.svg")))
        self.tb_cut.triggered.connect(self.editor.cut)

        self.tb_copy = QAction(self)
        self.tb_copy.setIcon(QIcon(resource_path("icons/copy.svg")))
        self.tb_copy.triggered.connect(self.editor.copy)

        self.tb_paste = QAction(self)
        self.tb_paste.setIcon(QIcon(resource_path("icons/paste.svg")))
        self.tb_paste.triggered.connect(self.editor.paste)

        self.tb_help = QAction(self)
        self.tb_help.setIcon(QIcon(resource_path("icons/help.svg")))
        self.tb_help.triggered.connect(self.show_help)

        self.tb_about = QAction(self)
        self.tb_about.setIcon(QIcon(resource_path("icons/about.svg")))
        self.tb_about.triggered.connect(self.show_about)

    def create_menus(self):
        mb = self.menuBar()

        file_menu = mb.addMenu(self.tr("file"))
        file_menu.addAction(self.menu_new)
        file_menu.addAction(self.menu_open)
        file_menu.addAction(self.menu_save)
        file_menu.addAction(self.menu_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.menu_exit)

        edit_menu = mb.addMenu(self.tr("edit"))
        edit_menu.addAction(self.menu_undo)
        edit_menu.addAction(self.menu_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.menu_cut)
        edit_menu.addAction(self.menu_copy)
        edit_menu.addAction(self.menu_paste)
        edit_menu.addSeparator()
        edit_menu.addAction(self.menu_select_all)

        run_menu = mb.addMenu(self.tr("run"))
        run_menu.addAction(self.menu_run)

        lang_menu = mb.addMenu(self.tr("language"))
        lang_menu.addAction(self.lang_ru_act)
        lang_menu.addAction(self.lang_en_act)

        help_menu = mb.addMenu(self.tr("help"))
        help_menu.addAction(self.help_act)
        help_menu.addAction(self.about_act)

    def create_toolbar(self):
        tb = QToolBar(self.tr("toolbar"))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tb.setIconSize(QSize(32, 32))

        tb.addAction(self.tb_run)
        tb.addSeparator()

        tb.addAction(self.tb_new)
        tb.addAction(self.tb_open)
        tb.addAction(self.tb_save)
        tb.addSeparator()

        tb.addAction(self.tb_undo)
        tb.addAction(self.tb_redo)
        tb.addSeparator()

        tb.addAction(self.tb_cut)
        tb.addAction(self.tb_copy)
        tb.addAction(self.tb_paste)
        tb.addSeparator()

        tb.addAction(self.tb_help)
        tb.addAction(self.tb_about)
        tb.addSeparator()

        tb.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                padding: 2px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.45);
                border-radius: 4px;
            }
            QToolButton:pressed {
                background: rgba(255, 255, 255, 0.25)
            }
        """)

    def switch_language(self, lang: str):
        if lang == self.current_lang:
            return
        self.load_translation(lang)
        self.lang_ru_act.setChecked(lang == "ru")
        self.lang_en_act.setChecked(lang == "en")

    def on_text_changed(self):
        if not self.is_dirty:
            self.is_dirty = True
            self.update_title()

    def update_title(self):
        title = self.tr("app_title")
        if self.current_file:
            title += f" — {os.path.basename(self.current_file)}"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    def update_cursor_status(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        
        line_str = self.tr('status_line')
        col_str = self.tr('status_column')
        
        self.status_label.setText(f"{line_str} {line} | {col_str} {column}")

    def maybe_save(self) -> bool:
        if not self.is_dirty:
            return True

        ret = QMessageBox.question(
            self,
            self.tr("unsaved_changes_title"),
            self.tr("unsaved_changes_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if ret == QMessageBox.StandardButton.Yes:
            return self.save_file()
        return ret == QMessageBox.StandardButton.No

    def new_file(self):
        if self.maybe_save():
            self.editor.clear()
            self.current_file = None
            self.is_dirty = False
            self.update_title()

    def open_file(self):
        if not self.maybe_save():
            return

        fname, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("open_file_title"),
            "",
            self.tr("file_filter")
        )
        if fname:
            try:
                with open(fname, encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
                self.current_file = fname
                self.is_dirty = False
                self.update_title()
            except Exception as e:
                QMessageBox.warning(self, self.tr("error_title"),
                                    f"{self.tr('cannot_open')}:\n{e}")

    def save_file(self) -> bool:
        if not self.current_file:
            return self.save_as_file()
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.is_dirty = False
            self.update_title()
            return True
        except Exception as e:
            QMessageBox.warning(self, self.tr("error_title"),
                                f"{self.tr('cannot_save')}:\n{e}")
            return False

    def save_as_file(self) -> bool:
        fname, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("save_as_title"),
            "",
            self.tr("file_filter")
        )
        if fname:
            self.current_file = fname
            return self.save_file()
        return False

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def show_help(self):
        help_text = self.get_detailed_help()
        QMessageBox.information(self, self.tr("help_help"), help_text)

    def get_detailed_help(self):
        sections = [
            ("help_section_features", "help_features"),
            ("help_section_hotkeys", "help_hotkeys"),
            ("help_section_analysis", "help_analysis"),
            ("help_section_i18n", "help_i18n"),
            ("help_section_interface", "help_interface"),
            ("help_section_additional", "help_additional"),
            ("help_section_technical", "help_technical")
        ]
        
        help_parts = [f"<b>{self.tr('app_title')}</b><br><br>"]
        
        for section_key, content_key in sections:
            section_title = self.tr(section_key)
            content = self.tr(content_key).replace('\n', '<br>')
            help_parts.append(f"{section_title}<br>{content}<br><br>")
        
        return ''.join(help_parts)

    def show_about(self):
        QMessageBox.about(self, self.tr("about_title"), self.tr("about_text"))

    def go_to_error(self, row, column):
        item0 = self.output_table.item(row, 0)
        if not item0:
            return
        data = item0.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        line_num, pos_start, pos_end = data
        try:
            line_num = int(line_num)
            pos_start = int(pos_start)
            pos_end = int(pos_end)
        except (TypeError, ValueError):
            return

        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, n=line_num - 1)
        cursor.movePosition(cursor.MoveOperation.Right, n=pos_start - 1)
        cursor.movePosition(
            cursor.MoveOperation.Right,
            cursor.MoveMode.KeepAnchor,
            pos_end - pos_start + 1,
        )
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()


    def run_analysis(self):
        self.output_table.clearSpans()
        self.output_table.setRowCount(0)
        self.analysis_result_label.setText("")
        text = self.editor.toPlainText()

        if not text.strip():
            self.output_table.setColumnCount(3)
            self.output_table.setRowCount(1)
            item = QTableWidgetItem(self.tr("analysis_empty"))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.output_table.setItem(0, 0, item)
            self.output_table.setSpan(0, 0, 1, 3)
            self.analysis_result_label.setText(self.tr("analysis_error_count").format(0))
            return

        scanner = Scanner(text)
        tokens = scanner.scan_tokens()
        result = analyze_syntax(tokens)

        self.output_table.setColumnCount(3)

        if result.ok:
            self.output_table.setRowCount(1)
            msg = QTableWidgetItem(self.tr("analysis_ok"))
            msg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.output_table.setItem(0, 0, msg)
            self.output_table.setSpan(0, 0, 1, 3)
            self.analysis_result_label.setText(self.tr("analysis_error_count").format(0))
        else:
            errors_num = len(result.errors)
            self.analysis_result_label.setText(self.tr("analysis_error_count").format(errors_num))
            self.output_table.setRowCount(errors_num)
            for i, err in enumerate(result.errors):
                fragment = QTableWidgetItem(err.fragment)
                location = QTableWidgetItem(
                    f"{self.tr('status_line')} {err.line}, "
                    f"{self.tr('err_position')} {err.start_pos}-{err.end_pos}"
                )
                description = QTableWidgetItem(err.message)
                pos_data = (err.line, err.start_pos, err.end_pos)
                fragment.setData(Qt.ItemDataRole.UserRole, pos_data)
                fragment.setBackground(QColor(255, 0, 0))
                location.setBackground(QColor(255, 0, 0))
                description.setBackground(QColor(255, 0, 0))
                self.output_table.setItem(i, 0, fragment)
                self.output_table.setItem(i, 1, location)
                self.output_table.setItem(i, 2, description)

        self.output_table.resizeColumnsToContents()
        self.output_table.horizontalHeader().setStretchLastSection(True)



def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())