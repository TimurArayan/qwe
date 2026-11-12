#!/bin/sh

case "${ROFI_RETV:-0}" in
    0)
        printf '%s\n' \
            'Сон' \
            'Перезагрузка' \
            'Выключение' \
            'Яркость (пока не настроена)' \
            'Режим работы (пока не настроен)'
        ;;
    1)
        case "$1" in
            'Сон')          exec systemctl suspend ;;
            'Перезагрузка') exec systemctl reboot ;;
            'Выключение')   exec systemctl poweroff ;;
            *) printf '%s\n' 'Пока не настроено' ;;
        esac
        ;;
esac