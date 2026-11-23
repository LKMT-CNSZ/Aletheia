#include "libraw/libraw.h"

#include <algorithm>
#include <cstring>

namespace {
constexpr int not_nikon_he = 1;
constexpr int unexpected_bitmap = 2;
constexpr int unexpected_exception = 3;
}

extern "C" __declspec(dllexport) int filminvert_decode_nikon_he(
    const wchar_t* path, int output_color, libraw_processed_image_t** output
) noexcept {
    *output = nullptr;
    try {
        LibRaw raw;
        int error = raw.open_file(path);
        if (error)
            return error;

        libraw_decoder_info_t decoder{};
        if (raw.get_decoder_info(&decoder) || !decoder.decoder_name ||
            std::strcmp(decoder.decoder_name, "nikon_he_load_raw()") != 0)
            return not_nikon_he;

        error = raw.unpack();
        if (error)
            return error;

        // Match the application's linear 16-bit rawpy processing settings.
        auto& params = raw.imgdata.params;
        const auto& daylight = raw.imgdata.rawdata.color.pre_mul;
        if (std::all_of(daylight, daylight + 3, [](float gain) { return gain > 0; }))
            std::copy_n(daylight, 4, params.user_mul);
        else
            params.use_camera_wb = 1;
        params.gamm[0] = params.gamm[1] = 1;
        params.no_auto_bright = 1;
        params.output_bps = 16;
        params.output_color = output_color;
        params.user_qual = 3;  // AHD
        params.adjust_maximum_thr = 0.75f;

        error = raw.dcraw_process();
        if (error)
            return error;

        auto* image = raw.dcraw_make_mem_image(&error);
        if (!image)
            return error ? error : unexpected_bitmap;
        if (image->type != LIBRAW_IMAGE_BITMAP || image->colors != 3 ||
            image->bits != 16 || !image->width || !image->height ||
            image->data_size != 6ULL * image->width * image->height) {
            LibRaw::dcraw_clear_mem(image);
            return unexpected_bitmap;
        }
        *output = image;
        return 0;
    } catch (...) {
        return unexpected_exception;
    }
}

extern "C" __declspec(dllexport) void filminvert_free_raw_image(
    libraw_processed_image_t* image
) noexcept {
    LibRaw::dcraw_clear_mem(image);
}

extern "C" __declspec(dllexport) const char* filminvert_raw_error(int error) noexcept {
    if (error == unexpected_bitmap)
        return "Unexpected 16-bit RGB output";
    if (error == unexpected_exception)
        return "Unexpected LibRaw exception";
    return LibRaw::strerror(error);
}
