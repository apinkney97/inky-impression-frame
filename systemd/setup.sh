#!/bin/bash
set -eux

if [ $(id -u) -ne 0 ]
then
  echo "This script must be run as root"
  exit 1
fi

ln -s /home/pi/framerunner/systemd/framerunner.service /etc/systemd/system/
systemctl start framerunner.service
systemctl enable framerunner.service

