#!/bin/sh

sleep 0.2
echo "Скрипт запущен" >> /tmp/zathura-resize.log
i3-msg '[class="(?i)zathura"] resize set width 890 px' >> /tmp/zathura-resize.log 2>&1
