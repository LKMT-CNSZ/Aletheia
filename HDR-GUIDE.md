# 片边测光与 HDR / Edge metering and HDR

Aletheia 3.2.0 正式版。旧工程保留原参数；请用副本试修并保留原片。

## 1. 自动测光排除片边

新导入默认「基础 → 自动测光 → 排除片边」。算法只检测与图像边缘相连、接近极值且有一致边界的扫描条带。检测不到可靠证据就使用全幅，不固定裁去画面的某个百分比。识别范围只影响自动黑白场和密度跨度估计，不裁减导出像素。真实画面有类似边框时可选择「全幅（兼容）」。切换会重新估计跨度并保留撤销记录。

旧工程和配方缺少此参数时继续全幅测光；不会静默改变旧成品。导入旧配方后若要启用修复，请显式切换自动测光方式。

## 2. 单张高光、阴影与黑白场

「基础 → 影调与颜色」新增阴影、高光、白场调整、黑场调整与高光柔化。阴影／高光／白场／黑场范围 −1 到 +1，零为关闭；高光柔化为 0–1。建议先确认片基与测光，再小幅调整。

操作在后续 SDR 截断之前的线性亮度上进行，尽量保留颜色比例。已在传感器或扫描阶段截断的信息无法凭单张操作恢复。HDR 导出与 HDR 显示会明确跳过用于 SDR 的高光柔化，保留浮点亮部。

## 3. 局部色调映射

「曲线 / HSL」新增局部 HDR 强度、作用范围和细节调整。它根据整个画面的低分辨率边缘保留亮度场调整局部明暗，强度零时不参与处理。100% 区域预览共享全图亮度场，避免每个小区域自行测光。

高强度仍可能放大颗粒或产生不自然的局部层次。建议从 0.2 左右开始，检查建筑轮廓、天空和细颗粒；并不承诺所有题材都没有光晕。

## 4. 多曝光合成

「文件 → 多曝光 HDR 合成」选择同一画面的 2–9 个实际曝光文件，填写拍摄时的相对 EV，例如 −2、0、+2。把同一个文件调亮调暗不增加采集信息。

- 负片：先合并线性透射数据，再扣除片基和反相。合成使用统一比例缩放保留透射比。
- 正像：合并线性场景数据，保留超过 1.0 的浮点亮部，打开后默认提供用于 SDR 预览的高光柔化。
- 可选平移对齐：只校正整数像素平移，不解决旋转、缩放或透视。超过画面 5% 的平移会拒绝。
- 可选重影抑制：与中间曝光进行一致性检查，不承诺处理所有运动、噪声或遮挡。
- 合成裁到各张的共同对齐区域；全部曝光都无有效端点信息的像素保留参考结果，并报告占比。
- 同布局大幅扫描可勾选「只读取当前帧区域」，仅支持无压缩、16bit RGB 线性 TIFF/FFF。该模式按线性 sRGB 解释；不要用于已经套用未知 gamma 的扫描。
- 合成区域上限为 2000 万像素，顺序解码以限制同时持有的曝光文件数；这是输入区域限制，并非整个进程的内存上限。解码器开始读取后可能不能立即取消。

输出为 float32 TIFF，包含线性 ICC、工作空间、源文件哈希、EV、平移量、共同区域和合成参数。不会覆盖已有文件或改写输入原片。合成结果可重新打开，按普通照片保存工程与加入 SDR 导出队列。

## 5. HDR 母版和屏幕预览

「文件 → 导出线性 HDR TIFF」保存当前帧的浮点线性母版，保留白平衡、影调、曲线/HSL、局部编辑和几何；高光柔化仅供 SDR，HDR 母版跳过该项。输出含线性 ICC 和元数据，亮度 1.0 对应名义参考白，数值允许高于 1.0。支持此类浮点 TIFF 的软件才能正确继续处理。

「文件 → HDR 屏幕预览」是独立 Windows 原生 Direct3D 11 / DXGI FP16 scRGB 显示窗口。窗口所在屏幕必须启用 Windows HDR。参考白可在 80–400 nits 调整；超过屏幕报告峰值的亮度采用柔和肩部映射。移动窗口、关闭系统 HDR 或图形设备出错时会重新检查并停止不适用的 HDR 显示，不会把普通 SDR 模拟标为 HDR。

HDR 预览不套用主窗口的 SDR 显示器 ICC 或 SDR 色域预览；Windows Advanced Color 管理该原生 HDR 表面的显示。SDR 主窗口和原有带 ICC 的 16bit TIFF 导出继续保留。HDR 母版目前通过单帧专用入口导出，批量队列仍输出 SDR TIFF。

本机实际验证了 FP16 显示通道创建和 SDR 状态拒绝。当前屏幕为 8bit SDR，HDR 屏上的实际亮度、色彩外观、切屏及不同显卡兼容性尚需硬件视觉验收。本功能在本版属于实验性显示功能。

## 工程兼容与安全

使用新测光或影调参数时保存工程版本 8、配方版本 6，旧程序会拒绝而非悄悄忽略。老工程的新增控制默认为关闭、全幅兼容测光。旧冻结队列仍按原引擎身份校验；升级后如被拒绝，复核后重新入队。

原片、工程与用户数据始终由用户持有。软件本地处理，无需上传照片。本次验证和源码分发仅含合成样例，私人 FFF 和诊断图不随包提供。

## English quick guide

New imports use conservative film-edge exclusion for automatic levels and density metering. Older projects retain legacy full-frame metering. This changes statistics only, never crops exported pixels.

Basic controls provide Shadows, Highlights, Whites, Blacks and SDR Highlight roll-off. Local tone mapping is available on Curves / HSL. Controls are disabled at zero and are saved per frame, in undo history, recipes and projects.

File → Multi-exposure HDR merge combines 2–9 actual exposures with explicit relative EV values. Negative transmission is merged before inversion. Positive scene radiance retains floating-point headroom. Optional alignment handles integer translation only; optional ghost rejection compares against the middle exposure. A common overlap crop and endpoint-loss report are recorded. Same-layout uncompressed linear scanner TIFF/FFF files can merge just the current frame. The merge region is limited to 20 MP.

File → Export linear HDR TIFF writes a float32 master with a linear ICC profile. SDR highlight roll-off is bypassed; the other edits are retained. HDR display preview uses native Windows DXGI FP16 scRGB and requires Windows HDR on the current display. The SDR main window and SDR TIFF queue remain available. Native FP16 creation and SDR refusal were tested on this machine; real HDR appearance requires validation on HDR hardware. This display feature is experimental in this release.

Implementation references: [Microsoft Advanced Color](https://learn.microsoft.com/en-us/windows/win32/direct3darticles/high-dynamic-range), [DXGI swap chains](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgifactory2-createswapchainforhwnd).

## 主窗口直接 HDR 调色

工具栏「主画布 HDR」在原画布开启 HDR；需先开启 Windows HDR。可直接调整曝光、颜色、曲线及局部影调，使用原有取样、缩放、撤销和照片导航。再次点击回到 SDR；系统 HDR 关闭或显示设备失效会自动回退。显示开关不改配方或导出格式。参考白默认跟随 Windows，可在 HDR 显示适配中手动设置，SDR 高光柔化不参与 HDR 呈现。

主直方图在开启 HDR 调色或主画布 HDR 后展开 SDR / HDR 分区，RGB 数据取自 SDR 压缩前的 HDR 主图。默认线性纵轴，点击标题或右键可切换对数纵轴；悬停查看 SDR 百分比或 HDR EV。右侧至少显示 +4 EV，随照片峰值或屏幕余量扩展至 +6 EV。浅色底条标出实际 HDR 显示时的屏幕余量。普通模式和查看原片时显示 SDR 直方图。统计来自当前预览或可见区域。大图 HDR 100% 预览受 768 MB 临时预算保护，超限自动回到适应窗口；导出尺寸不受影响。

显示器报告峰值缺失、低于 80 nit 或高于 10000 nit 时，HDR 预览暂按 1000 nit 估计，状态栏会明确提示。请使用 Windows HDR 校准核实屏幕能力；该估计不改动调色参数或 HDR 导出数据。

## TIFF 导出与无损压缩

「导出 TIFF / HDR…」仅提供 TIFF：SDR 16 位和 HDR Float32，各有「无损压缩 ZIP」与「不压缩」选项。默认无损压缩，记住上次选择的压缩方式；主画布 HDR 开启时默认选 HDR TIFF，文件菜单「导出线性 HDR TIFF」也默认 HDR。JPEG XR 与 Ultra HDR JPEG 已从导出界面移除。单张导出可同时保存普通 SDR JPEG 副本。整卷／批量导出继续使用 SDR 16 位无损 TIFF。

ZIP 使用标准 TIFF Deflate 无损压缩，不缩小分辨率、不降低位深。HDR 仍为 32 位浮点 RGB，保留线性 ICC、处理元数据与超过参考白的亮部；压缩文件可重新导入。未压缩数据每像素 12 字节，4320 × 5760 约 299 MB（285 MiB）。实际压缩率取决于画面、颗粒和噪声，仍可能较大。保存为 HDR TIFF 不保证所有看图软件都能按 HDR 亮度显示。


## HDR 显示适配与调色

本版替换 3.1.1 的全局预览增强，不会自动把旧预览增强写入照片。主画布 HDR 只切换显示。右侧「HDR」页显式勾选「启用 HDR 调色」后，亮部强度、起点、过渡、HDR 范围和 SDR 版本设置才参与处理；随每张/每帧编辑、撤销、工程、配方和批次影调同步保存。HDR TIFF 保存浮点调色数据。SDR TIFF 与普通预览使用同一 HDR 数据的 SDR 映射。参数关闭时保留原有算法。

基础 HDR 调色使用工程版本 9、配方版本 7；选择性调色和扩展曲线使用工程版本 10、配方版本 8；创意冲击力和高光淡化使用工程版本 11、配方版本 9；SDR 保色映射使用工程版本 12、配方版本 10。旧程序会拒绝不支持的新版本。单独将亮部强度归零不等于关闭所有 HDR 调色。扫描或拍摄已丢失的信息无法恢复。

「HDR 显示…」读取当前显示器状态、位深、系统 SDR 参考白与峰值报告；选择窗口所在屏幕对应的 DXGI 显卡，跨屏重新检测/创建显示通道。可按显示器在本机手动设置参考白、峰值。缺失或异常报告使用明确提示的估计值，需结合校准结果复核；不把估计当成实测。显示设置不写入照片或 HDR TIFF；HDR TIFF 的名义参考白为 203 nits，不烘焙某台屏幕的显示转换，不承诺不同查看器外观完全相同。

「对照 SDR 输出」只切换显示，不改照片。HDR 扩展直方图按最亮 RGB 通道统计，0 EV 为名义白；屏幕余量由峰值/参考白计算。「HDR 范围着色」显示黄色 HDR 亮部、红色超屏幕范围。SDR 屏可调 HDR、查看 SDR 版本并导出，无法替代 HDR 屏视觉检查。开启失败弹窗保留详情和 Windows 设置入口。多显示器/多显卡切换已做模拟与本机通道测试，尚未完成跨硬件视觉验收。本版 HDR 显示仍为实验功能。


## 胶片 HDR 预设

在「HDR」页选择「自然」「通透」「柔和」「明亮（保色）」「高光增强」。五个预设关闭创意冲击力与高光淡化，重置 HDR 扩展曲线及 SDR 对比／高光／降饱和参数，并开启 SDR 保色映射。保留已有曝光、白平衡、普通曲线、HSL、胶片设置和局部编辑，可撤销；已有工程不自动重写。

保存 HDR 母版时选择 **HDR TIFF - Float32 · 无损压缩 ZIP**。普通预览与 SDR TIFF 使用同一 HDR 主图的 SDR 映射；「SDR 保色映射」通过统一 RGB 增益压缩高光，减少逐通道裁切偏色，不改变 HDR 主图。HDR 名义参考白为 1.0 = 203 nits；本机屏幕校准不写入母版。扫描或拍摄已丢失的信息无法恢复。
