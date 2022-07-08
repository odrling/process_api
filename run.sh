#!/bin/sh
exec uvicorn server:app --reload $*
