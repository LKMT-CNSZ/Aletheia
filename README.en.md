# Aletheia

**3.2.1-rc1 local preview.** The prior stable release offers the [Windows installer, portable ZIP, source and checksums](https://github.com/LKMT-CNSZ/Aletheia/releases/tag/v3.2.0).

**A local film inversion and photo editing tool for Windows.**

Aletheia turns digitized color and black-and-white negatives into editable positive images. It brings RAW input, whole-strip scans, independent photo editing, batch proofing and ICC-tagged 16-bit TIFF export into one native Qt desktop application. Installer and portable ZIP editions include their own Python runtime.

Since version **3.0.1**, the app offers a **Simplified Chinese / English** interface. Choose a language from the toolbar or **View → Language / 语言**. The interface updates immediately and remembers your choice. Open photos, edits, history and queued exports remain in place; filenames, roll tags and other user-entered text keep their original spelling.

## Main features

- **Negative inversion:** color-negative, black-and-white-negative and positive modes; automatic film-base estimation or manual sampling; density range, contrast and film matrix presets.
- **Tone and color:** exposure, white balance, temperature, tint, RGB gains, a shared tone curve, eight-color HSL and saturation.
- **Single images and film strips:** automatic or manual frame layouts, independent frame parameters, frame ordering and whole-film export.
- **Geometry:** free or fixed-ratio crop, 90° rotation, fine straightening with multiple reference lines, film-edge suggestions and four-corner perspective correction.
- **Local editing:** clone repair, exposure brushes and linear gradients with radius, feather and strength controls. Local edits belong to each photo or frame.
- **Illumination and repair:** reference flat fields, strip-gap illumination estimation, vignette compensation, isolated dust repair and estimated underexposed-channel repair.
- **Color management:** linear sRGB and ProPhoto working spaces; sRGB, Adobe RGB (1998) and ProPhoto RGB TIFF output with matching ICC profiles; supported embedded input ICC profiles, display RGB ICC profiles and output gamut preview.
- **Chart calibration:** reference CSV import, individual or grid sampling, linear RGB matrix fitting, training and validation patch roles, and reusable correction profiles.
- **Photo library:** independent edits, ratings, pick / reject flags, roll tags, search, filters, source relinking, backup and restoration.
- **Batch workflow:** per-photo preparation, grouping, selected-parameter synchronization, independent EV adjustments, 4-up / 9-up proofing, visual review and an export queue with frozen parameter snapshots.
- **Delivery:** 16-bit TIFF, SDR JPEG, parameter recipes, film projects, PNG or JPEG contact sheets, batch summaries and project transfer packages that can include source files.

## Get started

1. Install the Windows x64 setup, or fully extract the portable ZIP. No separate Python installation is needed.
2. For the portable edition, run `启动 Aletheia.cmd` from the extracted folder.
3. Choose **English** in the toolbar. Open a photo with **Ctrl+O**, or drop multiple photos to populate the bottom navigator.
4. Choose an input mode and negative type. Check the film base, white balance and exposure before refining curves and color.
5. Use **Film edges / frames** for whole-strip scans; crop, straighten or correct perspective for individual frames.
6. Check important details at **100% view** and export an ICC-tagged **16-bit TIFF**.

For larger sets, open **Batch workflow** with **Ctrl+Shift+B**. Prepare photos individually, group compatible sources, synchronize only the intended parameters, refresh proofs and review before queueing exports. Queue snapshots retain the parameters that were current when each job was added.

## Useful shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl+O | Open an image |
| Ctrl+I | Open photo library / export queue |
| Ctrl+Shift+B | Open batch workflow |
| Ctrl+R | Crop |
| Ctrl+J | Local editing |
| Ctrl+K | Chart calibration |
| Ctrl+Shift+R | Input frames / film-edge alignment |
| Ctrl+Z / Ctrl+Shift+Z | Undo / redo |
| F / Ctrl+1 | Fit to window / 100% view |
| ← / → | Previous / next photo or frame |
| 0–5 / P / X / U | Rating / pick / reject / clear flag |
| Shift+R | Mark reviewed |
| Ctrl+Shift+S | Export 16-bit TIFF |

Navigation and rating shortcuts pause while you are editing text, numeric fields or combo boxes.

## Files and data

Installed editions use `%LOCALAPPDATA%\FilmInvertNative\data` for settings, sessions and the library, and `%LOCALAPPDATA%\FilmInvertNative\exports` as the default export folder. Writable portable editions use `data` and `out` beside the program; when those locations are not writable, they use the user folders above. **Help → Open user data folder** shows the actual location. Choose a different export folder on the Export tab.

Projects and library backups retain edits and source references. Keep the original images available. Use a project transfer package when the originals also need to travel with a project. Back up existing data before moving or combining installations.

Frozen export jobs from an older version are checked against their original engine signature. If a job is rejected after upgrading, review its edits and add a new job in the new version.

## Format and processing notes

TIFF, PNG, JPEG and RAW input are available; RAW support depends on the bundled decoder and the particular camera/file variant. Supported embedded input ICC conversion uses RGB matrix/TRC profiles. Some ICC profiles require conversion in another color-managed application first.

Automatic inversion is a starting point. Preview sampling and reduced-resolution dust detection can differ from a full-resolution export. Clone repair uses pixels from the image; dust and underexposed-channel repair are estimates. Chart error reports describe the sampled data and do not certify a device's color accuracy. Keep originals and check important results at full resolution.

The Chinese and English interface covers application menus, controls and dialogs. User content stays unchanged; low-level decoder errors, diagnostic tracebacks and existing report contents can retain their original language.

Processing runs locally. The native desktop application does not start a web server or upload photographs for processing. See `THIRD_PARTY` for bundled component notices and licenses.

## Short description for GitHub

A local film inversion and photo editing tool for Windows, with Chinese and English interfaces. Supports color and B&W negatives, RAW and whole-strip scans, independent photo editing, batch proofing and export, and ICC-tagged 16-bit TIFF output. Available as an installer or portable ZIP.

The toolbar **HDR canvas** switch enables native HDR directly in the editable main canvas. System HDR is required. Exposure, undo, sampling, zoom and photo navigation remain available. The histogram reports SDR output statistics; SDR proofing overlays are unavailable while the HDR canvas is active. Hardware visual QA is pending.

If the reported display peak is missing or outside 80–10000 nits, HDR preview explicitly assumes 1000 nits and reports this in the status bar. Use Windows HDR Calibration to verify your display. This estimate never changes grading parameters or HDR master pixels.

## TIFF export and lossless compression

**Export Photo** offers full-size SDR JPEG, SDR 16-bit TIFF, and HDR Float32 TIFF. Each TIFF variant supports **Lossless ZIP** or **Uncompressed**. Roll, library queue and batch export offer **TIFF only**, **JPEG only** or **TIFF and JPEG**. JPEG includes an sRGB ICC profile and uses the current SDR rendition of HDR edits. Roll and batch contact sheets can be saved as PNG or JPEG.

Standard TIFF Deflate compression preserves resolution, sample bits, ICC profiles and processing metadata. HDR remains 32-bit floating-point RGB with above-white highlights and can be reopened. Uncompressed 4320 x 5760 RGB pixels alone use 298,598,400 bytes; compression depends on content, grain and noise. HDR TIFF display brightness still depends on viewer support.




## First-view reveal and frame navigation

New negative imports initially show actual, masked source thumbnails in the frame strip. Each frame reveals from left to right with a soft edge over 1.6 seconds on first viewing and every time you switch to it and every time you switch to it and every time you switch to it, with RGB channels transitioning together. After playback its thumbnail becomes the current positive; unviewed frames remain negative. Completion is stored in the current user profile using source content, input interpretation and frame geometry. Switching to a different frame replays the reveal, including previously developed frames. Reopening an image or restoring an edit/project does not replay it. Changed source content or a newly defined frame gets a new identity.

Mouse, wheel, keyboard and grading can skip the animation and show the positive. Disabling View → Reveal on first viewing, or Windows animations, shows the result directly. Positive mode does not animate. Grades, histogram/sampling data and exported pixels are unaffected. Fit and 100% region previews retain the 2.1 MP source-preview budget and 8 MP HDR display-cache budget; larger previews show the result directly. Additional DNG compression support is not included.

The rc7 cached-texture, narrow-feather, background HDR preparation and 16 ms scheduling optimizations remain. The 1.6-second clock starts after HDR preparation; viewport changes or further interaction can cancel preparation. HDR blends display-linear scRGB endpoints and restores the actual edit on completion.


## Startup reveal

A 1.2-second left-to-right soft reveal develops the supplied red-and-white mascot logo, then fades into the editor. Processing modules import in a background thread; Qt widgets are created on the GUI thread. Slow initialization does not add another animation-length wait. Click the splash or press Escape to skip; Windows animation preferences are respected. Image arguments open once. Navigation reveal remains 1.6 seconds. A display-size copy of the supplied logo is bundled.


## Application icon

The application window, splash taskbar icon, shortcuts and installer use the supplied red-and-white FilmInvert film logo, with seven Windows ICO sizes from 16 to 256 pixels. The 1.2-second startup reveal continues to show the film mascot.


## Shortcut icon cache fix

Shortcuts use a dedicated ICO path containing the artwork hash, then notify Windows to refresh the item. This avoids reusing the old icon cache. Installer and window icons use the same new asset.




## HDR display adaptation and grading

This version replaces the global preview-only boost; it is not migrated into photos. Enable HDR grading in the HDR tab to save highlight strength, start, transition, HDR range and SDR rendition with each photo/frame. Projects, recipes, undo and batch tone synchronization retain these values. HDR TIFF stores the graded floating-point master. SDR previews and TIFF exports use the same master with SDR rendition mapping. Disabled defaults preserve the legacy pipeline.

HDR grading requires project version 9 / recipe version 7; older applications reject these versions. Display adaptation reads the window monitor, Windows SDR reference white and DXGI peak report, selects its GPU, and rechecks display changes. Per-display manual overrides stay on this computer. Missing/invalid reports use labeled estimates; calibrate and verify them. HDR TIFF keeps its authored 203-nit nominal white and does not bake device-specific adaptation. Viewer appearance may differ.

Compare SDR output, inspect the extended RGB-maximum histogram, or visualize HDR highlights in yellow and beyond-display values in red. 0 EV is nominal white. SDR displays can edit and export but cannot validate physical HDR appearance. Failure dialogs retain technical details and a Windows settings shortcut. HDR display remains experimental pending cross-device visual acceptance.


## Film HDR presets

Natural, Clear, Soft, Bright (color-safe) and Highlight lift enable HDR grading while preserving exposure, white balance, ordinary curves, HSL, film settings and local edits. They reset creative punch, highlight fading and HDR/SDR rendition controls, and enable color-safe SDR mapping. Undo, projects, recipes and batch tone synchronization retain these settings. Existing projects are not rewritten.

Choose **HDR TIFF - Float32 · Lossless ZIP** to save the floating-point master. SDR preview and SDR TIFF use the same master with SDR rendition mapping; color-safe mapping compresses highlights with a common RGB gain and does not alter the HDR master. Nominal white is 1.0 = 203 nits, independent of device-specific display adaptation. Presets cannot recover information lost during capture or scanning.
