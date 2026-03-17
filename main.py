from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"


def main() -> None:
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    from font_builder.build import main as build_main

    build_main()


if __name__ == "__main__":
    main()
