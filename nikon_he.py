"""Decode Nikon High Efficiency NEF with the bundled LibRaw snapshot."""
import ctypes as C
from functools import lru_cache
from pathlib import Path

import numpy as np


class _Image(C.Structure):
    _fields_ = [
        ('type', C.c_int), ('height', C.c_ushort), ('width', C.c_ushort),
        ('colors', C.c_ushort), ('bits', C.c_ushort), ('size', C.c_uint),
        ('data', C.c_ubyte * 1),
    ]


@lru_cache(maxsize=1)
def _library():
    path = Path(__file__).resolve().parent / 'raw_support' / 'nikon_he.dll'
    if not path.is_file():
        return None
    dll = C.CDLL(str(path))
    dll.filminvert_decode_nikon_he.argtypes = [
        C.c_wchar_p, C.c_int, C.POINTER(C.POINTER(_Image)),
    ]
    dll.filminvert_decode_nikon_he.restype = C.c_int
    dll.filminvert_free_raw_image.argtypes = [C.POINTER(_Image)]
    dll.filminvert_free_raw_image.restype = None
    dll.filminvert_raw_error.argtypes = [C.c_int]
    dll.filminvert_raw_error.restype = C.c_char_p
    return dll


def decode(path, output_color):
    dll = _library()
    if dll is None:
        return None

    result = C.POINTER(_Image)()
    status = dll.filminvert_decode_nikon_he(str(path), output_color, C.byref(result))
    if status == 1:
        return None  # The snapshot did not identify Nikon HE/HE* compression.
    if status:
        message = dll.filminvert_raw_error(status).decode('utf-8', errors='replace')
        raise RuntimeError(f'Nikon HE NEF: {message}')

    try:
        image = result.contents
        samples = (C.c_uint16 * (image.size // 2)).from_address(
            C.addressof(image) + _Image.data.offset
        )
        return np.ctypeslib.as_array(samples).reshape(image.height, image.width, 3).copy()
    finally:
        dll.filminvert_free_raw_image(result)
