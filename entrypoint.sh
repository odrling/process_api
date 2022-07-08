#!/bin/sh
. /opt/pragmadev/pragmaprocess/pragmaprocess-config.sh
Xvfb :1 &
export DISPLAY=:1
exec poetry run uvicorn server:app --reload $* 
