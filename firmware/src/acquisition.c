#include "acquisition.h"
#include <string.h>

uint16_t capture[CAPTURE_SAMPLES];
static uint16_t dma_ring[2 * BLOCK_SAMPLES];
volatile uint32_t stored_samples, acquired_samples, dropped_samples, adc_errors;
volatile uint8_t capture_done;
static uint8_t expected_half;
static uint32_t divisor = 1000;

uint32_t acquisition_set_rate(uint32_t requested) {
    if (requested < 1000U || requested > 96000U) return 0;
    divisor = (48000000U + requested / 2U) / requested;
    __HAL_TIM_SET_AUTORELOAD(&htim6, divisor - 1U);
    return divisor;
}
uint32_t acquisition_divisor(void) { return divisor; }

void acquisition_start(void) {
    stored_samples = acquired_samples = dropped_samples = adc_errors = 0;
    capture_done = expected_half = 0;
    __HAL_TIM_SET_COUNTER(&htim6, 0);
    __HAL_TIM_CLEAR_FLAG(&htim6, TIM_FLAG_UPDATE);
    if (HAL_ADC_Start_DMA(&hadc1, (uint32_t *)dma_ring, 2 * BLOCK_SAMPLES) != HAL_OK)
        fatal_error();
    if (HAL_TIM_Base_Start(&htim6) != HAL_OK) fatal_error();
}

static void completed_half(uint8_t half) {
    if (capture_done) return;
    if (half != expected_half) {
        adc_errors++;
        dropped_samples += BLOCK_SAMPLES; /* at least one half is missing */
        __HAL_TIM_DISABLE(&htim6);
        capture_done = 1;
        return;
    }
    expected_half ^= 1U;
    memcpy(&capture[stored_samples], &dma_ring[half * BLOCK_SAMPLES],
           BLOCK_SAMPLES * sizeof(uint16_t));
    uint32_t remaining = __HAL_DMA_GET_COUNTER(&hdma_adc1);
    if ((half == 0 && (remaining == 0 || remaining > BLOCK_SAMPLES)) ||
        (half == 1 && remaining <= BLOCK_SAMPLES)) {
        adc_errors++;
        __HAL_TIM_DISABLE(&htim6);
        capture_done = 1; /* copy overlapped DMA reuse; do not publish this half */
        return;
    }
    stored_samples += BLOCK_SAMPLES;
    acquired_samples += BLOCK_SAMPLES;
    if (stored_samples == CAPTURE_SAMPLES) {
        __HAL_TIM_DISABLE(&htim6);
        __DMB();
        capture_done = 1;
    }
}
void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *adc) {
    if (adc == &hadc1) completed_half(0);
}
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *adc) {
    if (adc == &hadc1) completed_half(1);
}
void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *adc) {
    if (adc == &hadc1) {
        adc_errors++;
        __HAL_TIM_DISABLE(&htim6);
        capture_done = 1; /* unknown loss count: error flag invalidates capture */
    }
}
void acquisition_finish(void) {
    if (HAL_TIM_Base_Stop(&htim6) != HAL_OK) fatal_error();
    if (HAL_ADC_Stop_DMA(&hadc1) != HAL_OK) fatal_error();
    __DMB();
}
