import sys
from importlib import import_module
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> None:
    build_main = import_module("font_builder.build").main
    build_main()


if __name__ == "__main__":
    main()
