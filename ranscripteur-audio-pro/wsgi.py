#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée WSGI pour la production.

Lancement :
    cd ranscripteur-audio-pro
    gunicorn wsgi:application
"""

from app import create_app

application = create_app()

if __name__ == '__main__':
    application.run()
