import re


class MatchHit:
    def __init__(self, fragment, line, column, length, abs_start, abs_end):
        self.fragment = fragment
        self.line = line
        self.column = column
        self.length = length
        self.abs_start = abs_start
        self.abs_end = abs_end


def _line_and_column(text, index):
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index) + 1
    column = index - line_start + 1
    return line, column


def find_literal_matches(text, needle):
    if not needle:
        return []
    result = []
    n = len(needle)
    pos = 0
    while True:
        i = text.find(needle, pos)
        if i == -1:
            break
        line, col = _line_and_column(text, i)
        result.append(
            MatchHit(needle, line, col, n, i, i + n)
        )
        pos = i + n
    return result


def find_matches(text, pattern, flags=0):
    result = []
    for m in re.finditer(pattern, text, flags):
        start = m.start()
        frag = m.group(0)
        line, col = _line_and_column(text, start)
        end = m.end()
        result.append(
            MatchHit(frag, line, col, len(frag), start, end)
        )
    return result
