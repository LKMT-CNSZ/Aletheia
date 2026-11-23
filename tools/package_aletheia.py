"""Package the Aletheia Windows distribution and compile its installer."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_aletheia_installer import build
from build_compat import BUNDLE, ROOT, VERSION


def package(bundle, destination):
    manifest = json.loads((bundle / "file-manifest.json").read_text("utf-8"))
    with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=5) as archive:
        for name in sorted([*manifest["files"], "file-manifest.json"]):
            archive.write(bundle / name, f"Aletheia/{name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path,
                        default=ROOT / "build/release-tools/InnoSetup/ISCC.exe")
    args = parser.parse_args()
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    portable = release / f"Aletheia-{VERSION}-win64.zip"
    package(BUNDLE, portable)
    installer, _ = build(portable, args.iscc.resolve())
    print(f"Portable ZIP: {portable}\nInstaller: {installer}")
