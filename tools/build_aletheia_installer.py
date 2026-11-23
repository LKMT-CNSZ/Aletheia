"""Build the Aletheia Windows installer from its portable release ZIP."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ICON = "filminvert-native-856209a72631.ico"
MANIFEST = "file-manifest.json"
UPGRADER = "app/installer_upgrade.py"


def extract_bundle(archive, bundle):
    prefix = "Aletheia/"
    with ZipFile(archive) as zipped:
        manifest_bytes = zipped.read(prefix + MANIFEST)
        manifest = json.loads(manifest_bytes)
        files = manifest["files"]
        entries = [entry.filename for entry in zipped.infolist() if not entry.is_dir()]
        expected = {prefix + name for name in files} | {prefix + MANIFEST}
        if set(entries) != expected or len(entries) != len(expected):
            raise ValueError("ZIP does not match the portable release file manifest")

        for name, checksum in files.items():
            parts = name.split("/")
            if (
                any(part in ("", ".", "..") for part in parts)
                or any(char in name for char in '\\:{};"\r\n')
                or parts[0] not in {"app", "runtime", "THIRD_PARTY"} and len(parts) != 1
                or parts[:2] == ["app", "build"]
                or "__pycache__" in parts
                or name in (MANIFEST, "installed-layout.json")
            ):
                raise ValueError(f"Invalid portable release path: {name}")
            payload = zipped.read(prefix + name)
            if hashlib.sha256(payload).hexdigest() != checksum:
                raise ValueError(f"Portable release checksum mismatch: {name}")
            target = bundle.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    return manifest


def build(archive, compiler):
    stage = Path(tempfile.mkdtemp(prefix="aletheia-installer-", dir=ROOT / "build"))
    bundle = stage / "Aletheia"
    manifest = extract_bundle(archive, bundle)
    version = (bundle / "VERSION.txt").read_text("utf-8-sig").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-rc\d+)?", version):
        raise ValueError(f"Invalid application version: {version}")
    portable = json.loads((bundle / "portable-layout.json").read_text("utf-8-sig"))
    if portable["version"] != version or portable["architecture"] != "Windows x64":
        raise ValueError("Portable layout does not match the x64 release version")

    # Extend the portable upgrade helper's existing brand check for this installer.
    # Other parts of the helper and all photo processing files come from the ZIP.
    upgrade_path = bundle / UPGRADER
    upgrade = upgrade_path.read_bytes()
    old_check = b"not item['DisplayName'].startswith('FilmInvert Native ')"
    new_check = b"not item['DisplayName'].startswith(('FilmInvert Native ', 'Aletheia '))"
    if upgrade.count(old_check) == 1:
        upgrade = upgrade.replace(old_check, new_check)
        upgrade_path.write_bytes(upgrade)
        manifest["files"][UPGRADER] = hashlib.sha256(upgrade).hexdigest()
    elif new_check not in upgrade:
        raise ValueError("Review the upgrade helper before packaging the renamed product")

    (bundle / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    (stage / "VERSION.txt").write_text(version + "\n", "utf-8")
    script_dir = stage / "tools"
    script_dir.mkdir()
    for name in ("stable-setup.iss", "installer-ui.iss", "ChineseSimplified.isl"):
        shutil.copy2(ROOT / "tools" / name, script_dir / name)
    shutil.copytree(ROOT / "tools/installer-assets", script_dir / "installer-assets")
    (stage / "assets").mkdir()
    shutil.copy2(bundle / "app/assets" / ICON, stage / "assets" / ICON)

    layout = json.loads((ROOT / "tools/installed-layout.json").read_text("utf-8-sig"))
    layout["version"] = version
    (script_dir / "installed-layout.json").write_text(json.dumps(layout, indent=2), "utf-8")
    rows = []
    for name in sorted([*manifest["files"], MANIFEST]):
        path = PurePosixPath(name)
        destination = "{app}" + ("\\" + str(Path(path.parent)) if path.parent.parts else "")
        rows.append(f'Source: "{{#BundleDir}}\\{Path(path)}"; DestDir: "{destination}"; Flags: ignoreversion')
    (script_dir / "stable-files.iss").write_text("\n".join(rows) + "\n", "utf-8-sig")

    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    basename = f"Aletheia-{version}-setup-win64"
    with (stage / "compile.log").open("wb") as log:
        result = subprocess.run(
            [str(compiler), "/Qp", "/DProductName=Aletheia", f"/DBundleDir={bundle}",
             f"/DAppFileVersion={version.split('-')[0]}", f"/O{release}", f"/F{basename}",
             str(script_dir / "stable-setup.iss")],
            cwd=stage, stdout=log, stderr=subprocess.STDOUT
        )
    if result.returncode:
        raise RuntimeError(f"Inno Setup compilation failed. See {stage / 'compile.log'}")
    return release / (basename + ".exe"), stage


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portable_zip", type=Path)
    parser.add_argument("--iscc", type=Path, default=ROOT / "build/release-tools/InnoSetup/ISCC.exe")
    args = parser.parse_args()
    output, staging = build(args.portable_zip.resolve(), args.iscc.resolve())
    print(f"Installer: {output}\nStaging: {staging}")
