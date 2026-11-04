#ifndef PCM1808_CONFIG_H
#define PCM1808_CONFIG_H
#include "stm32l4xx_hal.h"
/* Prepared and compiled only. Main ADC firmware does not invoke this module.
   External 12.288 MHz oscillator clocks PCM1808 MASTER, MD1/MD0=1/1, FMT=0.
   Receive BCK PA8, LRCK PA9, DOUT PA10 (all AF13), 2 slots x 32, data 24.
   NO MCU-generated audio clock, NO USB application stack is claimed. */
HAL_StatusTypeDef pcm1808_prepare_slave_rx(void);
HAL_StatusTypeDef pcm1808_receive_words(uint32_t *buffer, uint16_t words);
int32_t pcm1808_sign_extend_right24(uint32_t raw);
#endif
