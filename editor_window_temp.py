import json
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from scanner import Scanner, TOKEN_TYPES
from parser import analyze_syntax
from editor_window import EditorWindow


class TemporaryEditorWindow(EditorWindow):
    def __init__(self):
        self.feedback_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "analysis_feedback.json",
        )
        self.feedback_db = self._load_feedback_db()
        super().__init__()
        self._install_temp_actions()

    def _install_temp_actions(self):
        self.menu_run_incorrect = QAction("Прогнать неверные строки", self)
        self.menu_run_incorrect.triggered.connect(self.run_incorrect_lines_review)

        self.menu_run_all_lines = QAction("Прогнать все строки", self)
        self.menu_run_all_lines.triggered.connect(self.run_all_lines_review)

        self.menu_run_var_file = QAction("Прогнать строки из var.txt", self)
        self.menu_run_var_file.triggered.connect(self.run_var_file_lines_review)

        run_menu = None
        for action in self.menuBar().actions():
            if action.text() == self.tr("run"):
                run_menu = action.menu()
                break
        if run_menu is not None:
            run_menu.addSeparator()
            run_menu.addAction(self.menu_run_incorrect)
            run_menu.addAction(self.menu_run_all_lines)
            run_menu.addAction(self.menu_run_var_file)

        if getattr(self, "_main_toolbar", None):
            self._main_toolbar.addSeparator()
            self._main_toolbar.addAction(self.menu_run_var_file)

    def run_analysis(self):
        return self._run_analysis_internal(ask_feedback=True, source_line=None)

    def _run_analysis_internal(self, ask_feedback=True, source_line=None):
        self._refresh_output_tabs_headers()
        self.lexer_table.clearSpans()
        self.lexer_table.setRowCount(0)
        self.parser_table.clearSpans()
        self.parser_table.setRowCount(0)
        self.lexer_summary_label.setText("")
        self.parser_summary_label.setText("")
        text = self.editor.toPlainText()

        if not text.strip():
            self.lexer_table.setColumnCount(4)
            self.lexer_table.setRowCount(1)
            item = self._centered_item(self.tr("analysis_empty"))
            self.lexer_table.setItem(0, 0, item)
            self.lexer_table.setSpan(0, 0, 1, 4)

            self.parser_table.setColumnCount(3)
            self.parser_table.setRowCount(1)
            item2 = self._centered_item(self.tr("analysis_empty"))
            self.parser_table.setItem(0, 0, item2)
            self.parser_table.setSpan(0, 0, 1, 3)
            self.lexer_summary_label.setText(self.tr("lexer_token_count").format(0))
            self.parser_summary_label.setText(self.tr("analysis_error_count").format(0))
            return None

        scanner = Scanner(text)
        tokens = scanner.scan_tokens()
        result = analyze_syntax(tokens)

        self._fill_lexer_table(tokens)
        self._fill_parser_table(result)

        self.lexer_table.resizeColumnsToContents()
        self.lexer_table.horizontalHeader().setStretchLastSection(True)
        self.parser_table.resizeColumnsToContents()
        self.parser_table.horizontalHeader().setStretchLastSection(True)

        if ask_feedback:
            target_line = source_line if source_line is not None else text
            return self._ask_and_store_feedback(target_line, tokens, result)
        return None

    def _centered_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _collect_errors(self, tokens, result):
        errors = []
        for err in result.errors:
            errors.append(
                {
                    "source": "analyzer",
                    "line": err.line,
                    "start": err.start_pos,
                    "end": err.end_pos,
                    "message": err.message,
                    "fragment": err.fragment,
                }
            )
        return errors

    def _ask_and_store_feedback(self, line_text, tokens, result):
        errors = self._collect_errors(tokens, result)
        errors_num = len(errors)
        preview = line_text.strip().replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:120] + "..."

        answer = QMessageBox.question(
            self,
            "Оценка результата",
            (
                f"Строка:\n{preview or '<пусто>'}\n\n"
                f"Показано ошибок: {errors_num}\n\n"
                "Да — ошибки верные (супер)\n"
                "Нет — ошибки неверные\n"
                "Отмена — не сохранять оценку"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )

        if answer == QMessageBox.StandardButton.Cancel:
            return answer

        status = "correct" if answer == QMessageBox.StandardButton.Yes else "incorrect"
        self.feedback_db[line_text] = {
            "status": status,
            "errors": errors,
        }
        self._save_feedback_db()
        return answer

    def run_incorrect_lines_review(self):
        lines = [line for line, meta in self.feedback_db.items() if meta.get("status") == "incorrect"]
        self._run_lines_review(lines, "неверные")

    def run_all_lines_review(self):
        text_lines = [line.strip() for line in self.editor.toPlainText().splitlines()]
        lines = [line for line in text_lines if line]
        self._run_lines_review(lines, "все")

    def run_var_file_lines_review(self):
        var_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "var.txt")
        if not os.path.exists(var_path):
            QMessageBox.warning(self, "var.txt", f"Файл не найден:\n{var_path}")
            return
        try:
            with open(var_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            QMessageBox.warning(self, "var.txt", f"Не удалось прочитать файл:\n{exc}")
            return
        cases = self._split_cases_by_empty_lines(content)
        self._run_lines_review(cases, "var.txt")

    def _split_cases_by_empty_lines(self, content):
        cases = []
        current = []
        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                if current:
                    cases.append("\n".join(current))
                    current = []
                continue
            current.append(line)
        if current:
            cases.append("\n".join(current))
        return cases

    def _run_lines_review(self, lines, mode_name):
        if not lines:
            QMessageBox.information(self, "Проверка строк", f"Нет строк для режима: {mode_name}.")
            return

        original_text = self.editor.toPlainText()
        stopped = False
        for idx, line in enumerate(lines, start=1):
            self.editor.setPlainText(line)
            answer = self._run_analysis_internal(ask_feedback=True, source_line=line)
            if answer == QMessageBox.StandardButton.Cancel:
                stopped = True
                break

            QMessageBox.information(
                self,
                "Прогон строк",
                f"Обработано: {idx}/{len(lines)}",
            )

        self.editor.setPlainText(original_text)
        if stopped:
            QMessageBox.information(self, "Прогон строк", "Прогон остановлен пользователем.")
        else:
            QMessageBox.information(self, "Прогон строк", "Прогон завершен.")

    def _load_feedback_db(self):
        if not os.path.exists(self.feedback_path):
            return {}
        try:
            with open(self.feedback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_feedback_db(self):
        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(self.feedback_db, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TemporaryEditorWindow()
    window.show()
    sys.exit(app.exec())
