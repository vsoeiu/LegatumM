#!/bin/bash

# 1. Instala dependencias con pip3
pip3 install -r requirements.txt

# 2. Inicia la aplicación usando python3 y gunicorn
python3 -m gunicorn app:app