#include "acquisition.h"
#include <stddef.h>

/* Wire v1: little-endian, 64-byte header, uint16 payload, CRC32/ISO-HDLC. */
typedef struct {
    char magic[4];
    uint16_t version, header_bytes;
    uint32_t sequence, capture_id, first_sample, count, fs_num, fs_den;
    uint32_t format, adc_bits, vref_uv, total_samples, dropped_samples;
    uint32_t adc_errors, flags, payload_bytes;
} Header;
_Static_assert(sizeof(Header) == 64, "wire header layout changed");
static uint32_t sequence;
static uint32_t crc_update(uint32_t crc, const void *data, size_t n) {
    const uint8_t *bytes = data;
    while (n--) {
        crc ^= *bytes++;
        for (unsigned bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ (0xEDB88320U & (0U - (crc & 1U)));
    }
    return crc;
}
static void send_bytes(const void *data, uint16_t n) {
    if (HAL_UART_Transmit(&huart2, (uint8_t *)data, n, 1000) != HAL_OK)
        fatal_error(); /* transport failure cannot be reported over a dead UART */
}
void protocol_send_capture(uint32_t id) {
    /* Transmit even a zero-length failed capture, so the host receives errors. */
    for (uint32_t first = 0; first < stored_samples || first == 0; first += BLOCK_SAMPLES) {
        uint32_t n = stored_samples - first;
        if (n > BLOCK_SAMPLES) n = BLOCK_SAMPLES;
        uint32_t flags = 16U; /* VREF is assumed, not measured */
        if (first == 0) flags |= 1U | 4U; /* first; gap before every burst */
        if (first + n == stored_samples) flags |= 2U;
        if (adc_errors || dropped_samples || stored_samples != CAPTURE_SAMPLES) flags |= 8U;
        Header header = {
            {'I','E','P','1'}, 1, sizeof(Header), sequence++, id, first, n,
            48000000U, acquisition_divisor(), 1, 12, 3300000,
            acquired_samples, dropped_samples, adc_errors, flags, n * 2U
        };
        uint32_t crc = crc_update(0xFFFFFFFFU, &header, sizeof(header));
        crc = crc_update(crc, &capture[first], n * 2U) ^ 0xFFFFFFFFU;
        send_bytes(&header, sizeof(header));
        if (n) send_bytes(&capture[first], (uint16_t)(n * 2U));
        send_bytes(&crc, sizeof(crc));
        if (flags & 2U) break;
    }
}
