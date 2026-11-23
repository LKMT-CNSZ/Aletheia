# Aletheia 3.2.0 正式版

- 双语安装器恢复同一张实拍胶片的负片、去色罩、正片三阶段示意。
- 改进横向、纵向整卷扫描的自动切帧与帧间片基取样。重估片基时保留已拟合的密度跨度和黑白场，避免亮度跳变。
- 调整一帧的片边时保留其余帧的调色、裁切、照明校正和正片缩略图。切帧仍使用 1.6 秒柔边显影。
- SDR 16 位 TIFF、HDR 浮点 TIFF 支持无损 ZIP 压缩或不压缩，还可同时保存普通 JPEG 副本。

## English

The bilingual installer restores the three-stage example from a real film scan. Roll detection now supports both directions. Re-metering preserves fitted exposure, and adjusting one frame's borders preserves the other frames' edits and developed thumbnails. TIFF export provides lossless ZIP or uncompressed output and an optional SDR JPEG companion.
