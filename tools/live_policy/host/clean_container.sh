#!/bin/bash
# clean_container.sh <container>: kill every process except PID 1 (only between runs!)
docker exec "$1" bash -c 'for p in $(ps -eo pid=); do [ "$p" -ne 1 ] && [ "$p" -ne $$ ] && kill -9 "$p" 2>/dev/null; done; rm -f /tmp/.X99-lock /tmp/.X11-unix/X99; true'
docker exec "$1" bash -c 'ps -eo pid,stat,cmd | grep -v defunct | grep -vE "ps -eo|bash -c" | head'
