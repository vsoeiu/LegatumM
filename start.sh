#!/bin/bash

# 1. Instala dependencias desde requirements.txt
pip install -r requirements.txt

# 2. Inicia la aplicación usando Gunicorn
gunicorn app:app