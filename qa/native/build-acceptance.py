#!/usr/bin/env python3
"""The report owner is the sole writer of acceptance and report outputs."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
runpy.run_path(str(ROOT/'scripts/build-report.py'),run_name='__main__')
