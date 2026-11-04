#include "pcm1808_config.h"

static SAI_HandleTypeDef hsai1a;
static DMA_HandleTypeDef hdma_sai1a;

HAL_StatusTypeDef pcm1808_prepare_slave_rx(void) {
    /* board_init() has PLL VCO=192 MHz, P=7. Kernel=27.428571 MHz.
       This clocks internal logic only; external BCK/LRCK determine sampling. */
    RCC_PeriphCLKInitTypeDef clocks = {0};
    clocks.PeriphClockSelection = RCC_PERIPHCLK_SAI1;
    clocks.Sai1ClockSelection = RCC_SAI1CLKSOURCE_PLL;
    if (HAL_RCCEx_PeriphCLKConfig(&clocks) != HAL_OK) return HAL_ERROR;
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_DMA2_CLK_ENABLE();
    __HAL_RCC_SAI1_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF13_SAI1;
    HAL_GPIO_Init(GPIOA, &gpio);
    hdma_sai1a.Instance = DMA2_Channel1;
    hdma_sai1a.Init.Request = DMA_REQUEST_1;
    hdma_sai1a.Init.Direction = DMA_PERIPH_TO_MEMORY;
    hdma_sai1a.Init.PeriphInc = DMA_PINC_DISABLE;
    hdma_sai1a.Init.MemInc = DMA_MINC_ENABLE;
    hdma_sai1a.Init.PeriphDataAlignment = DMA_PDATAALIGN_WORD;
    hdma_sai1a.Init.MemDataAlignment = DMA_MDATAALIGN_WORD;
    hdma_sai1a.Init.Mode = DMA_CIRCULAR;
    hdma_sai1a.Init.Priority = DMA_PRIORITY_VERY_HIGH;
    if (HAL_DMA_Init(&hdma_sai1a) != HAL_OK) return HAL_ERROR;
    hsai1a.Instance = SAI1_Block_A;
    hsai1a.Init.AudioMode = SAI_MODESLAVE_RX;
    hsai1a.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai1a.Init.OutputDrive = SAI_OUTPUTDRIVE_DISABLE;
    hsai1a.Init.NoDivider = SAI_MASTERDIVIDER_ENABLE;
    hsai1a.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
    hsai1a.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_48K; /* informational in slave */
    hsai1a.Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    hsai1a.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai1a.Init.CompandingMode = SAI_NOCOMPANDING;
    hsai1a.Init.TriState = SAI_OUTPUT_NOTRELEASED;
    __HAL_LINKDMA(&hsai1a, hdmarx, hdma_sai1a);
    HAL_NVIC_SetPriority(DMA2_Channel1_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(DMA2_Channel1_IRQn);
    HAL_NVIC_SetPriority(SAI1_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(SAI1_IRQn);
    return HAL_SAI_InitProtocol(&hsai1a, SAI_I2S_STANDARD,
                               SAI_PROTOCOL_DATASIZE_24BIT, 2);
}
HAL_StatusTypeDef pcm1808_receive_words(uint32_t *buffer, uint16_t words) {
    /* Application must implement half/full/error callbacks before using this.
       Keep BOTH channels. Four-word multiples ensure halves contain full frames. */
    if (!buffer || words < 4 || words % 4 || ((uintptr_t)buffer & 3U)) return HAL_ERROR;
    return HAL_SAI_Receive_DMA(&hsai1a, (uint8_t *)buffer, words);
}
int32_t pcm1808_sign_extend_right24(uint32_t raw) {
    /* SAI DR data is right aligned; verify on hardware before calibrated use. */
    uint32_t value = raw & 0xFFFFFFU;
    return (value & 0x800000U) ? (int32_t)(value - 0x1000000U) : (int32_t)value;
}
void DMA2_Channel1_IRQHandler(void) { HAL_DMA_IRQHandler(&hdma_sai1a); }
void SAI1_IRQHandler(void) { HAL_SAI_IRQHandler(&hsai1a); }
