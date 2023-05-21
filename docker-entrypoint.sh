#!/bin/bash

#cd /api

python manage.py db migrate
python manage.py db upgrade

echo should_have_upgraded_db