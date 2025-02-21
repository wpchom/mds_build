/*!
    \file    gd32e11x_redirect.c
    \brief   redirect optional for gd32e11x

    \version 2023-12-31, V1.2.0, firmware for GD32E11x
*/

#include "gd32e11x.h"

void nvic_vector_table_set(uint32_t nvic_vict_tab, uint32_t offset)
{
    (void)(nvic_vict_tab);
    (void)(offset);
}
