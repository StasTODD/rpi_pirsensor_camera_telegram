#!/bin/bash

script_file=main.py
script_path=/home/stastodd/projects/rpi_pirsensor_camera_telegram/
script_pid=$(ps -axx | grep pirsensor_camera_telegram | grep main.py | awk '{print $1}')

if [ $script_pid ]
  then
    echo "rpi_pirsensor_camera_telegram script is running, it have pid: $script_pid"
  else
    cd $script_path ; ./$script_file &
fi

