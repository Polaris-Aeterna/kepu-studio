#!/usr/bin/env python3
"""Run the kepu toolkit straight from the plugin folder (no install): python3 kepu_run.py <command> …"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kepu.__main__ import main  # noqa: E402

sys.exit(main())
