#ifndef ACQUISITION_H
#define ACQUISITION_H
#include "stm32l4xx_hal.h"
#include <stdint.h>
#define CAPTURE_SAMPLES 8192U
#define BLOCK_SAMPLES 512U
extern UART_HandleTypeDef huart2;
extern ADC_HandleTypeDef hadc1;
extern DMA_HandleTypeDef hdma_adc1;
extern TIM_HandleTypeDef htim6;
extern uint16_t capture[CAPTURE_SAMPLES];
extern volatile uint32_t stored_samples, acquired_samples, dropped_samples, adc_errors;
extern volatile uint8_t capture_done;
void board_init(void);
void fatal_error(void);
uint32_t acquisition_set_rate(uint32_t requested);
uint32_t acquisition_divisor(void);
void acquisition_start(void);
void acquisition_finish(void);
void protocol_send_capture(uint32_t capture_id);
#endif
