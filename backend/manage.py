#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django (migrations, seed, tests…)."""

import os
import sys


def main() -> None:
    """Exécute la commande d'administration demandée."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
