import os
import sys
import json

from PyQt6.QtCore import Qt, QSize, QRect, QEvent
from PyQt6.QtGui import (
    QFont,
    QKeySequence,
    QAction,
    QIcon,
    QColor,
    QPalette,
    QTextCursor,
    QTextCharFormat,
    QPainter,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QSizePolicy,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QLabel,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
    QPushButton,
    QToolButton,
    QTabWidget,
    QTextEdit,
    QDialog,
    QTextBrowser,
    QDialogButtonBox,
)

import re

from regex_search import find_literal_matches, find_matches
from scanner import Scanner, TOKEN_TYPES
from parser import ParseResult
from semantic_analysis import analyze_program


class LineNum(QWidget):
    def __init__(self, editor: "NumberedPlainTextEdit"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class NumberedPlainTextEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNum(self)
        self.line_number_area.setAutoFillBackground(True)
        self._sync_line_number_palette()
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area_cursor)
        self.update_line_number_area_width()

    def line_number_area_width(self):
        digits = 1
        n = max(1, self.blockCount())
        v = n
        while v >= 10:
            v //= 10
            digits += 1
        space = 8 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        w = self.line_number_area_width()
        self.line_number_area.setGeometry(QRect(0, cr.top(), w, cr.height()))
        self.line_number_area.raise_()

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            w = self.line_number_area_width()
            self.line_number_area.update(0, rect.y(), w, rect.height())

    def update_line_number_area_cursor(self):
        self.line_number_area.update(
            0,
            0,
            self.line_number_area.width(),
            self.line_number_area.height(),
        )

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._sync_line_number_palette()
            self.line_number_area.update()
        super().changeEvent(event)

    def _sync_line_number_palette(self):
        self.line_number_area.setPalette(self.palette())

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        pal = self.palette()
        zalivka = pal.color(QPalette.ColorRole.Window)
        if not zalivka.isValid():
            zalivka = pal.color(QPalette.ColorRole.Mid)
        painter.fillRect(event.rect(), zalivka)
        block = self.firstVisibleBlock()
        if not block.isValid():
            return
        block_number = block.blockNumber()
        top = int(self.blockBoundingRect(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(pal.color(QPalette.ColorRole.WindowText))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    height,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class SearchPopup(QWidget):
    MODE_PLAIN = 0
    MODE_REGEX = 1

    REGEX_PRESETS = [
        ("search_regex_preset_custom", None),
        (
            "search_regex_preset_cn_postal",
            r"^\d{6}$",
        ),
        (
            "search_regex_preset_unionpay",
            r"^(62|81)\d{14,17}$",
        ),
        (
            "search_regex_preset_hsl",
            r"^hsl\(\s*(360|3[0-5]\d|[12]?\d{1,2})\s*,\s*(100|[1-9]?\d)%\s*,\s*(100|[1-9]?\d)%\s*\)$",
        ),
    ]

    def __init__(self, editor_window: "EditorWindow"):
        super().__init__(
            editor_window,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self._win = editor_window
        self.setMinimumWidth(380)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        row_find = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_btn = QPushButton()
        self.find_btn.setFixedWidth(88)
        self.find_btn.clicked.connect(self._on_find)
        self.find_input.returnPressed.connect(self._on_find)
        row_find.addWidget(self.find_input, 1)
        row_find.addWidget(self.find_btn)
        outer.addLayout(row_find)

        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        outer.addWidget(self.mode_combo)

        self.regex_extra = QWidget()
        re_lay = QVBoxLayout(self.regex_extra)
        re_lay.setContentsMargins(0, 0, 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        re_lay.addWidget(self.preset_combo)
        outer.addWidget(self.regex_extra)
        self.regex_extra.hide()

        self._suppress_preset_signal = False
        self._build_mode_combo()
        self._build_preset_combo()
        self.setObjectName("SearchPopup")
        self.setStyleSheet(
            "#SearchPopup { background: palette(base); "
            "border: 1px solid palette(mid); border-radius: 6px; }"
        )

    def _build_mode_combo(self):
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItem("", self.MODE_PLAIN)
        self.mode_combo.addItem("", self.MODE_REGEX)
        self.mode_combo.setCurrentIndex(self.MODE_PLAIN)
        self.mode_combo.blockSignals(False)

    def _build_preset_combo(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for key, _pat in self.REGEX_PRESETS:
            self.preset_combo.addItem("", _pat)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def retranslate(self):
        self.find_btn.setText(self._win.tr("search_find_btn"))
        self.mode_combo.setItemText(0, self._win.tr("search_mode_plain"))
        self.mode_combo.setItemText(1, self._win.tr("search_mode_regex"))
        for i, (key, _pat) in enumerate(self.REGEX_PRESETS):
            self.preset_combo.setItemText(i, self._win.tr(key))

    def _on_mode_changed(self, _index: int):
        is_regex = self.mode_combo.currentData() == self.MODE_REGEX
        self.regex_extra.setVisible(is_regex)
        self.adjustSize()
        if is_regex:
            self._apply_preset_to_field()

    def _on_preset_changed(self, _index: int):
        if self._suppress_preset_signal:
            return
        self._apply_preset_to_field()

    def _apply_preset_to_field(self):
        if self.mode_combo.currentData() != self.MODE_REGEX:
            return
        pat = self.preset_combo.currentData()
        if pat is None:
            return
        self._suppress_preset_signal = True
        self.find_input.setText(pat)
        self._suppress_preset_signal = False

    def _on_find(self):
        text = self.find_input.text()
        if self.mode_combo.currentData() == self.MODE_PLAIN:
            self._win.run_search_query(literal=True, query=text)
        else:
            self._win.run_search_query(literal=False, query=text)


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.current_file = None
        self.is_dirty = False
        self.current_lang = "ru"
        self.trans = {}
        self._search_popup = None

        self.setMinimumHeight(500)
        self.setMinimumWidth(700)
        self.setWindowIcon(QIcon(resource_path("icons/logo.svg")))

        self.setGeometry(200, 100, 1100, 750)

        self.init_ui()
        self.create_actions()

        self.load_translation(self.current_lang)

        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.textChanged.connect(self._clear_editor_search_highlights)
        self.lexer_table.cellClicked.connect(
            lambda r, c: self.go_to_error_cell(self.lexer_table, r, c)
        )
        self.parser_table.cellClicked.connect(
            lambda r, c: self.go_to_error_cell(self.parser_table, r, c)
        )
        self.semantic_table.cellClicked.connect(
            lambda r, c: self.go_to_error_cell(self.semantic_table, r, c)
        )
        self.search_table.cellClicked.connect(
            lambda r, c: self.go_to_error_cell(self.search_table, r, c)
        )
        
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
        self.menu_search.setText(self.tr("search_action"))
        if getattr(self, "search_tool_button", None):
            self.search_tool_button.setToolTip(self.tr("search_action"))

        if getattr(self, "semantic_ast_label", None):
            self.semantic_ast_label.setText(self.tr("semantic_ast_heading"))
        if getattr(self, "semantic_ast_view_tree_rb", None):
            self.semantic_ast_view_tree_rb.setText(
                self.tr("semantic_ast_format_tree")
            )
            self.semantic_ast_view_json_rb.setText(
                self.tr("semantic_ast_format_json")
            )
            if hasattr(self, "_semantic_ast_tree_text"):
                self._refresh_semantic_ast_display()

        if getattr(self, "output_tabs", None):
            self.output_tabs.setTabText(0, self.tr("output_tab_lexer"))
            self.output_tabs.setTabText(1, self.tr("output_tab_parser"))
            self.output_tabs.setTabText(2, self.tr("output_tab_semantic"))
            self.output_tabs.setTabText(3, self.tr("output_tab_search"))

        self.menuBar().clear()
        self.create_menus()

        for toolbar in self.findChildren(QToolBar):
            self.removeToolBar(toolbar)
        self.create_toolbar()

        self._refresh_output_tabs_headers()

        if self._search_popup is not None:
            self._search_popup.retranslate()

        self.update_cursor_status()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.splitter)

        self.editor = NumberedPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setTabStopDistance(
            4 * self.editor.fontMetrics().horizontalAdvance(" ")
        )
        self.splitter.addWidget(self.editor)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)

        self.output_tabs = QTabWidget()
        self.output_tabs.setFont(QFont("Consolas", 10))

        self.lexer_summary_label = QLabel()
        self.lexer_summary_label.setWordWrap(True)
        self.lexer_table = QTableWidget()
        self._configure_results_table(self.lexer_table, 4)
        lexer_tab = QWidget()
        lexer_layout = QVBoxLayout(lexer_tab)
        lexer_layout.setContentsMargins(4, 4, 4, 4)
        lexer_layout.addWidget(self.lexer_summary_label)
        lexer_layout.addWidget(self.lexer_table)
        self.output_tabs.addTab(lexer_tab, "Lexer")

        self.parser_summary_label = QLabel()
        self.parser_summary_label.setWordWrap(True)
        self.parser_table = QTableWidget()
        self._configure_results_table(self.parser_table, 3)
        parser_tab = QWidget()
        parser_layout = QVBoxLayout(parser_tab)
        parser_layout.setContentsMargins(4, 4, 4, 4)
        parser_layout.addWidget(self.parser_summary_label)
        parser_layout.addWidget(self.parser_table)
        self.output_tabs.addTab(parser_tab, "Parser")

        self.semantic_table = QTableWidget()
        self._configure_results_table(self.semantic_table, 3)
        self.semantic_ast_header = QWidget()
        ast_header_row = QHBoxLayout(self.semantic_ast_header)
        ast_header_row.setContentsMargins(0, 0, 0, 0)
        self.semantic_ast_label = QLabel()
        self.semantic_ast_view_tree_rb = QRadioButton()
        self.semantic_ast_view_json_rb = QRadioButton()
        self.semantic_ast_view_tree_rb.setChecked(True)
        self.semantic_ast_view_group = QButtonGroup(self.semantic_ast_header)
        self.semantic_ast_view_group.setExclusive(True)
        self.semantic_ast_view_group.addButton(self.semantic_ast_view_tree_rb, 0)
        self.semantic_ast_view_group.addButton(self.semantic_ast_view_json_rb, 1)
        self.semantic_ast_view_tree_rb.toggled.connect(self._refresh_semantic_ast_display)
        self.semantic_ast_view_json_rb.toggled.connect(self._refresh_semantic_ast_display)
        ast_header_row.addWidget(self.semantic_ast_label)
        ast_header_row.addWidget(self.semantic_ast_view_tree_rb)
        ast_header_row.addWidget(self.semantic_ast_view_json_rb)
        ast_header_row.addStretch(1)
        self.semantic_ast = QTextEdit()
        self.semantic_ast.setReadOnly(True)
        self.semantic_ast.setFont(QFont("Consolas", 10))
        self.semantic_ast.setMinimumHeight(160)
        self.semantic_table.setMinimumHeight(56)
        self.semantic_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        semantic_tab = QWidget()
        semantic_layout = QVBoxLayout(semantic_tab)
        semantic_layout.setContentsMargins(4, 4, 4, 4)
        self._semantic_splitter = QSplitter(Qt.Orientation.Vertical)
        self._semantic_splitter.setChildrenCollapsible(True)
        semantic_table_host = QWidget()
        st_host_lay = QVBoxLayout(semantic_table_host)
        st_host_lay.setContentsMargins(0, 0, 0, 0)
        st_host_lay.setSpacing(0)
        st_host_lay.addWidget(self.semantic_table)
        semantic_ast_host = QWidget()
        ast_host_lay = QVBoxLayout(semantic_ast_host)
        ast_host_lay.setContentsMargins(0, 0, 0, 0)
        ast_host_lay.setSpacing(4)
        ast_host_lay.addWidget(self.semantic_ast_header)
        ast_host_lay.addWidget(self.semantic_ast, 1)
        self._semantic_splitter.addWidget(semantic_table_host)
        self._semantic_splitter.addWidget(semantic_ast_host)
        self._semantic_splitter.setStretchFactor(0, 0)
        self._semantic_splitter.setStretchFactor(1, 1)
        self._semantic_splitter.setSizes([130, 340])
        semantic_layout.addWidget(self._semantic_splitter)
        self.output_tabs.addTab(semantic_tab, "Semantic")

        self.search_summary_label = QLabel()
        self.search_summary_label.setWordWrap(True)
        self.search_table = QTableWidget()
        self._configure_results_table(self.search_table, 3)
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        search_layout.setContentsMargins(4, 4, 4, 4)
        search_layout.addWidget(self.search_summary_label)
        search_layout.addWidget(self.search_table)
        self.output_tabs.addTab(search_tab, "Search")

        self.output_panel = QWidget()
        output_layout = QVBoxLayout(self.output_panel)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_tabs)
        self.splitter.addWidget(self.output_panel)

        self.splitter.setSizes([550, 200])

    def _configure_results_table(self, table, columns):
        table.setColumnCount(columns)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setFont(QFont("Consolas", 11))

    def _clear_editor_search_highlights(self):
        self.editor.setExtraSelections([])

    def _apply_editor_search_highlights(self, matches):
        if not matches:
            self._clear_editor_search_highlights()
            return
        doc = self.editor.document()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(180, 180, 180))
        selections = []
        for m in matches:
            cur = QTextCursor(doc)
            cur.setPosition(m.abs_start)
            cur.setPosition(m.abs_end, QTextCursor.MoveMode.KeepAnchor)
            extra = QTextEdit.ExtraSelection()
            extra.cursor = cur
            extra.format = fmt
            selections.append(extra)
        self.editor.setExtraSelections(selections)

    def _position_search_popup(self, popup: "SearchPopup") -> None:
        popup.adjustSize()
        pw = popup.width()
        ph = popup.height()
        fg = self.frameGeometry()
        margin = 8
        x = fg.right() - pw - margin
        tb = getattr(self, "_main_toolbar", None)
        if tb is not None:
            y = tb.mapToGlobal(tb.rect().bottomLeft()).y() + 2
        else:
            y = fg.top() + margin
        x = max(fg.left() + margin, min(x, fg.right() - pw - margin))
        y = max(fg.top() + margin, min(y, fg.bottom() - ph - margin))
        popup.move(x, y)

    def create_actions(self):
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

        self.menu_run = QAction(self)
        self.menu_run.setShortcut(QKeySequence("F5"))
        self.menu_run.triggered.connect(self.run_analysis)

        self.menu_search = QAction(self)
        self.menu_search.setShortcut(QKeySequence("Ctrl+F"))
        self.menu_search.triggered.connect(self.open_search_popup)

        self.lang_ru_act = QAction(self)
        self.lang_ru_act.setCheckable(True)
        self.lang_ru_act.setChecked(True)
        self.lang_ru_act.triggered.connect(lambda: self.switch_language("ru"))

        self.lang_en_act = QAction(self)
        self.lang_en_act.setCheckable(True)
        self.lang_en_act.triggered.connect(lambda: self.switch_language("en"))

        self.help_act = QAction(self)
        self.help_act.setShortcut(QKeySequence("F1"))
        self.help_act.triggered.connect(self.show_help)

        self.about_act = QAction(self)
        self.about_act.triggered.connect(self.show_about)

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
        edit_menu.addSeparator()
        edit_menu.addAction(self.menu_search)

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
        self._main_toolbar = tb
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

        self.search_tool_button = QToolButton(tb)
        self.search_tool_button.setIcon(QIcon(resource_path("icons/search.svg")))
        self.search_tool_button.setIconSize(QSize(32, 32))
        self.search_tool_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.search_tool_button.setToolTip(self.tr("search_action"))
        self.search_tool_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_tool_button.clicked.connect(self.open_search_popup)
        tb.addWidget(self.search_tool_button)

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
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("help_help"))
        dlg.resize(640, 480)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(True)
        browser.setHtml(help_text)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()

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

    def _refresh_output_tabs_headers(self):
        self.lexer_table.setHorizontalHeaderLabels([
            self.tr("table_code"),
            self.tr("table_type"),
            self.tr("table_lexeme"),
            self.tr("table_location"),
        ])
        self.parser_table.setHorizontalHeaderLabels([
            self.tr("table_err_fragment"),
            self.tr("table_err_location"),
            self.tr("table_err_desc"),
        ])
        self.semantic_table.setHorizontalHeaderLabels([
            self.tr("table_err_fragment"),
            self.tr("table_err_location"),
            self.tr("table_err_desc"),
        ])
        self.search_table.setHorizontalHeaderLabels([
            self.tr("table_search_fragment"),
            self.tr("table_search_position"),
            self.tr("table_search_length"),
        ])

    def go_to_error_cell(self, table, row, column):
        item0 = table.item(row, 0)
        if not item0:
            return
        data = item0.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        if isinstance(data, dict) and data.get("type") == "abs":
            try:
                start = int(data["start"])
                end = int(data["end"])
            except (KeyError, TypeError, ValueError):
                return
            cursor = self.editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(cursor)
            self.editor.setFocus()
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

    def open_search_popup(self):
        if self._search_popup is None:
            self._search_popup = SearchPopup(self)
        self._search_popup.retranslate()
        self._position_search_popup(self._search_popup)
        self._search_popup.show()
        self._search_popup.raise_()
        self._search_popup.activateWindow()
        self._search_popup.find_input.setFocus()

    def run_search_query(self, *, literal: bool, query: str):
        self._refresh_output_tabs_headers()
        self.search_table.clearSpans()
        self.search_table.setRowCount(0)
        self._clear_editor_search_highlights()

        text = self.editor.toPlainText()
        if not text.strip():
            self.search_summary_label.setText(self.tr("search_count").format(0))
            self.search_table.setColumnCount(3)
            self.search_table.setRowCount(1)
            item = QTableWidgetItem(self.tr("search_empty_text"))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_table.setItem(0, 0, item)
            self.search_table.setSpan(0, 0, 1, 3)
            self.output_tabs.setCurrentIndex(3)
            return

        if literal:
            matches = find_literal_matches(text, query)
        else:
            if not query.strip():
                QMessageBox.warning(
                    self,
                    self.tr("error_title"),
                    self.tr("search_regex_empty"),
                )
                return
            try:
                re.compile(query)
            except re.error as e:
                QMessageBox.warning(
                    self, self.tr("error_title"), self.tr("search_regex_error").format(e)
                )
                return
            matches = find_matches(text, query, re.MULTILINE)

        n = len(matches)
        self.search_summary_label.setText(self.tr("search_count").format(n))
        self.search_table.setColumnCount(3)

        if n == 0:
            self.search_table.setRowCount(1)
            item = QTableWidgetItem(self.tr("search_no_matches"))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_table.setItem(0, 0, item)
            self.search_table.setSpan(0, 0, 1, 3)
            self.search_table.resizeColumnsToContents()
            self.search_table.horizontalHeader().setStretchLastSection(True)
            self.output_tabs.setCurrentIndex(3)
            return

        self.search_table.setRowCount(n)
        for i, m in enumerate(matches):
            fragment = QTableWidgetItem(m.fragment)
            location = QTableWidgetItem(
                f"{self.tr('status_line')} {m.line}, "
                f"{self.tr('status_column')} {m.column}"
            )
            length_item = QTableWidgetItem(str(m.length))
            pos_data = {"type": "abs", "start": m.abs_start, "end": m.abs_end}
            fragment.setData(Qt.ItemDataRole.UserRole, pos_data)

            self.search_table.setItem(i, 0, fragment)
            self.search_table.setItem(i, 1, location)
            self.search_table.setItem(i, 2, length_item)

        self.search_table.resizeColumnsToContents()
        self.search_table.horizontalHeader().setStretchLastSection(True)
        self._apply_editor_search_highlights(matches)
        self.output_tabs.setCurrentIndex(3)

    def run_analysis(self):
        self._clear_editor_search_highlights()
        self._refresh_output_tabs_headers()
        self.lexer_table.clearSpans()
        self.lexer_table.setRowCount(0)
        self.parser_table.clearSpans()
        self.parser_table.setRowCount(0)
        self.lexer_summary_label.setText("")
        self.parser_summary_label.setText("")
        self.semantic_ast.clear()
        self.semantic_ast_label.setText("")
        self.semantic_table.clearSpans()
        self.semantic_table.setRowCount(0)
        text = self.editor.toPlainText()

        if not text.strip():
            self.lexer_table.setColumnCount(4)
            self.lexer_table.setRowCount(1)
            item = QTableWidgetItem(self.tr("analysis_empty"))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lexer_table.setItem(0, 0, item)
            self.lexer_table.setSpan(0, 0, 1, 4)
            self.parser_table.setColumnCount(3)
            self.parser_table.setRowCount(1)
            item2 = QTableWidgetItem(self.tr("analysis_empty"))
            item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.parser_table.setItem(0, 0, item2)
            self.parser_table.setSpan(0, 0, 1, 3)
            self.semantic_table.setColumnCount(3)
            self.semantic_table.setRowCount(1)
            item3 = QTableWidgetItem(self.tr("analysis_empty"))
            item3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.semantic_table.setItem(0, 0, item3)
            self.semantic_table.setSpan(0, 0, 1, 3)
            self.semantic_ast_label.setText(self.tr("semantic_ast_heading"))
            self._semantic_ast_tree_text = self.tr("semantic_ast_absent") + "\n"
            self._semantic_ast_json_text = "{}\n"
            self.semantic_ast_view_group.blockSignals(True)
            self.semantic_ast_view_tree_rb.setChecked(True)
            self.semantic_ast_view_group.blockSignals(False)
            self._refresh_semantic_ast_display()
            self.lexer_summary_label.setText(self.tr("lexer_token_count").format(0))
            self.parser_summary_label.setText(self.tr("analysis_error_count").format(0))
            return

        scanner = Scanner(text)
        tokens = scanner.scan_tokens()
        sem = analyze_program(tokens)
        result = ParseResult(sem.syntax_ok, sem.syntax_errors)

        self._fill_lexer_table(tokens)
        self._fill_parser_table(result)
        self._fill_semantic_panel(sem)

        self.lexer_table.resizeColumnsToContents()
        self.lexer_table.horizontalHeader().setStretchLastSection(True)
        self.parser_table.resizeColumnsToContents()
        self.parser_table.horizontalHeader().setStretchLastSection(True)
        self.semantic_table.resizeColumnsToContents()
        self.semantic_table.horizontalHeader().setStretchLastSection(True)

    def _fill_lexer_table(self, tokens):
        self.lexer_table.clearSpans()
        self.lexer_table.setColumnCount(4)
        n = len(tokens)
        self.lexer_summary_label.setText(self.tr("lexer_token_count").format(n))
        self.lexer_table.setRowCount(n)
        err_code = TOKEN_TYPES["ERROR"][0]
        err_bg = QColor(255, 0, 0)
        for i, tok in enumerate(tokens):
            code_item = QTableWidgetItem(str(tok.code))
            type_item = QTableWidgetItem(tok.type_name)
            lex_item = QTableWidgetItem(tok.lexeme)
            loc = (
                f"{self.tr('status_line')} {tok.line}, "
                f"{self.tr('err_position')} {tok.start_pos}-{tok.end_pos}"
            )
            loc_item = QTableWidgetItem(loc)
            pos_data = (tok.line, tok.start_pos, tok.end_pos)
            code_item.setData(Qt.ItemDataRole.UserRole, pos_data)
            if tok.code == err_code:
                for item in (code_item, type_item, lex_item, loc_item):
                    item.setBackground(err_bg)
            self.lexer_table.setItem(i, 0, code_item)
            self.lexer_table.setItem(i, 1, type_item)
            self.lexer_table.setItem(i, 2, lex_item)
            self.lexer_table.setItem(i, 3, loc_item)

    def _fill_parser_table(self, result):
        self.parser_table.clearSpans()
        self.parser_table.setColumnCount(3)
        if result.ok:
            self.parser_table.setRowCount(1)
            msg = QTableWidgetItem(self.tr("analysis_ok"))
            msg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.parser_table.setItem(0, 0, msg)
            self.parser_table.setSpan(0, 0, 1, 3)
            self.parser_summary_label.setText(self.tr("analysis_error_count").format(0))
        else:
            errors_num = len(result.errors)
            self.parser_summary_label.setText(
                self.tr("analysis_error_count").format(errors_num)
            )
            self.parser_table.setRowCount(errors_num)
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
                self.parser_table.setItem(i, 0, fragment)
                self.parser_table.setItem(i, 1, location)
                self.parser_table.setItem(i, 2, description)

    def _refresh_semantic_ast_display(self, _index=None):
        if not hasattr(self, "_semantic_ast_tree_text"):
            return
        if self.semantic_ast_view_json_rb.isChecked():
            mode = "json"
        else:
            mode = "tree"
        if mode == "json":
            self.semantic_ast.setPlainText(self._semantic_ast_json_text)
        else:
            self.semantic_ast.setPlainText(self._semantic_ast_tree_text)

    def _fill_semantic_panel(self, sem):
        self.semantic_ast_label.setText(self.tr("semantic_ast_heading"))
        n_sem = len(sem.semantic_errors)
        self.semantic_table.clearSpans()
        self.semantic_table.setColumnCount(3)
        if n_sem == 0:
            self.semantic_table.setRowCount(1)
            msg = QTableWidgetItem(self.tr("semantic_no_errors"))
            msg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.semantic_table.setItem(0, 0, msg)
            self.semantic_table.setSpan(0, 0, 1, 3)
        else:
            self.semantic_table.setRowCount(n_sem)
            for i, err in enumerate(sem.semantic_errors):
                fragment = QTableWidgetItem(err.fragment)
                location = QTableWidgetItem(
                    f"{self.tr('status_line')} {err.line}, "
                    f"{self.tr('err_position')} {err.start_pos}-{err.end_pos}"
                )
                description = QTableWidgetItem(err.message)
                pos_data = (err.line, err.start_pos, err.end_pos)
                fragment.setData(Qt.ItemDataRole.UserRole, pos_data)
                err_bg = QColor(255, 0, 0)
                fragment.setBackground(err_bg)
                location.setBackground(err_bg)
                description.setBackground(err_bg)
                self.semantic_table.setItem(i, 0, fragment)
                self.semantic_table.setItem(i, 1, location)
                self.semantic_table.setItem(i, 2, description)

        self._semantic_ast_tree_text = sem.ast_tree_text.rstrip() + "\n"
        self._semantic_ast_json_text = sem.ast_json_text.rstrip() + "\n"
        self.semantic_ast_view_group.blockSignals(True)
        self.semantic_ast_view_tree_rb.setChecked(True)
        self.semantic_ast_view_group.blockSignals(False)
        self._refresh_semantic_ast_display()


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