from pathlib import Path
import shutil


BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"


def main():
    shutil.copytree(BASE_DIR / "static", DIST_DIR, dirs_exist_ok=True)
    shutil.copytree(
        BASE_DIR / "data" / "cache",
        DIST_DIR / "data" / "cache",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        BASE_DIR / "outputs",
        DIST_DIR / "outputs",
        dirs_exist_ok=True,
    )


if __name__ == "__main__":
    main()
