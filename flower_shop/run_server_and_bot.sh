#!/bin/bash

# Start Django server in background
cd /workspaces/workspace
python manage.py runserver 0.0.0.0:5000 &
django_pid=$!

# Wait a bit for Django to start
sleep 2

# Start Telegram bot
cd /workspaces/workspace
python telegram_bot/bot.py

# If bot exits, kill Django server
kill $django_pid
