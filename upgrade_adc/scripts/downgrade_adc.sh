#!/bin/bash

dcmanagerPath="/mystic/telemetry/DCManager/conf"
if [ -d "$dcmanagerPath" ]; then
  cd $dcmanagerPath
  sed -e "s/APP_VERSION:.*/APP_VERSION: 0.0.000/" application.yml > application.yml.new
  mv application.yml.new application.yml
  echo "dcmanager version downgrade successfully !"
fi

lockboxPath="/mystic/lockbox/conf/"
if [ -d "$lockboxPath" ]; then
  cd $lockboxPath
  sed -e "s/lockbox_version:.*/lockbox_version: 0.0.000/" lockbox.yml > lockbox.yml.new
  mv lockbox.yml.new lockbox.yml
  echo "lockbox version downgrade successfully !"
fi

if [ -d "/mystic/radar" ]; then
  rm -rf /mystic/radar
  echo "radar removed successfully !"
fi

aceWar="/usr/lib/vmware-marvin/marvind/webapps/ace.war"
if [ -f  "$aceWar" ]; then
  rm $aceWar
  echo "acd.war removed successfully !"
fi

adcPatchesPath="/mystic/telemetry/DCManager/tmp/adc_patches"
if [ ! -d "$adcPatchesPath" ]; then
  mkdir -p $adcPatchesPath
fi

