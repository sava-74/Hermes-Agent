#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""herLayStart.py - Запуск Hermes Agent на русском языке"""

import os
import subprocess

# Устанавливаем русский язык
os.environ["HERMES_LANGUAGE"] = "ru"

# Запускаем Hermes CLI
subprocess.run([".venv\\Scripts\\python.exe", "cli.py"])
