#include "acquisition.h"

int main(void) {
    board_init();
    uint32_t capture_id = 0, requested = 0;
    uint8_t parsing_rate = 0, bad_rate = 0;
    for (;;) {
        uint8_t byte;
        if (HAL_UART_Receive(&huart2, &byte, 1, 20) != HAL_OK) continue;
        if (byte == 'R') {
            parsing_rate = 1; bad_rate = 0; requested = 0;
        } else if (parsing_rate && byte >= '0' && byte <= '9') {
            if (requested > 96000U) bad_rate = 1;
            else requested = requested * 10U + (uint32_t)(byte - '0');
        } else if (parsing_rate && byte == '\n') {
            if (bad_rate || !acquisition_set_rate(requested)) {
                parsing_rate = 0;
                /* Ignore next C until a valid rate arrives; never mislabel fs. */
                bad_rate = 1;
            } else { parsing_rate = 0; bad_rate = 0; }
        } else if (parsing_rate) {
            parsing_rate = 0; bad_rate = 1;
        } else if (byte == 'C' && !bad_rate) {
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_SET);
            acquisition_start();
            while (!capture_done) { __WFI(); }
            acquisition_finish();
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_RESET);
            protocol_send_capture(capture_id++);
        }
    }
}
