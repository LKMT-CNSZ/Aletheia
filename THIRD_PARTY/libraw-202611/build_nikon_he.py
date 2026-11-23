"""Rebuild the two Nikon HE DLLs from an x64 MSVC developer prompt."""
import argparse
from hashlib import file_digest
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
SUPPORT = HERE.parents[1] / 'app' / 'raw_support'
SOURCE = HERE / 'LibRaw-a9a14b1970d188c25dade81f8326ff00a6e33649.zip'


def build(folder, support):
    with ZipFile(SOURCE) as archive:
        archive.extractall(folder)
    source = folder / 'LibRaw-master'
    makefile = (source / 'Makefile.msvc').read_text(encoding='utf-8')
    files = re.findall(r'^object\\\w+_st\.obj:\s+(src\\[^\r\n]+)', makefile, re.M)
    if len(files) != 81 or len(set(files)) != len(files):
        raise ValueError('Unexpected LibRaw source list')
    (source / 'object').mkdir(exist_ok=True)
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join([
        '/nologo /c /utf-8 /O2 /EHsc /MP8 /MT /I. /DWIN32',
        '/DLIBRAW_WIN32_DLLDEFS /DLIBRAW_BUILDLIB /openmp /Foobject\\',
        *files,
    ]) + '\n', encoding='ascii')
    subprocess.run(['cl', '@' + str(rsp)], cwd=source, check=True)
    library = folder / 'filminvert_libraw_202611'
    subprocess.run([
        'link', '/nologo', '/DLL', f'/out:{library}.dll', f'/implib:{library}.lib',
        *map(str, sorted((source / 'object').glob('*.obj'))),
    ], cwd=folder, check=True)
    subprocess.run([
        'cl', '/nologo', '/utf-8', '/O2', '/EHsc', '/MD', '/LD', f'/I{source}',
        str(support / 'nikon_he.cpp'), f'{library}.lib', '/link', '/out:nikon_he.dll',
    ], cwd=folder, check=True)
    for dll in (library.with_suffix('.dll'), folder / 'nikon_he.dll'):
        shutil.copyfile(dll, support / dll.name)
        with dll.open('rb') as stream:
            print(dll.name, file_digest(stream, 'sha256').hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support-dir', type=Path, default=SUPPORT)
    support = parser.parse_args().support_dir.resolve()
    with TemporaryDirectory(dir=Path.cwd(), prefix='filminvert-libraw-') as directory:
        build(Path(directory), support)
