"""TIFF export choices; identifiers stay independent of translated UI labels."""
def export_formats():
    from i18n import tr as _t
    return {
        str(_t('SDR TIFF - 16位 · 无损压缩 ZIP (*.tif *.tiff)')):(False,'deflate'),
        str(_t('SDR TIFF - 16位 · 不压缩 (*.tif *.tiff)')):(False,'none'),
        str(_t('HDR TIFF - Float32 · 无损压缩 ZIP (*.tif *.tiff)')):(True,'deflate'),
        str(_t('HDR TIFF - Float32 · 不压缩 (*.tif *.tiff)')):(True,'none'),
    }
