import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
ANTLR_DIR = ROOT / "antlr"
GRAMMAR = ANTLR_DIR / "RepeatWhile.g4"
OUT_DIR = ANTLR_DIR / "generated"
JAR = ANTLR_DIR / "antlr-4.9.3-complete.jar"


def main():
    if not JAR.exists():
        print(f"ANTLR jar not found: {JAR}")
        print("Download: https://www.antlr.org/download/antlr-4.9.3-complete.jar")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java",
        "-jar",
        str(JAR),
        "-Dlanguage=Python3",
        "-visitor",
        "-no-listener",
        "-o",
        str(OUT_DIR),
        str(GRAMMAR),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)
    print("ANTLR generation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
