#!/bin/bash

# . .venv/bin/activate
cd src
gunicorn main:gunicorn_app --bind 0.0.0.0:13534
