"""The verification tests replay recordings; they never touch the network.

VERIFY_OFFLINE=1 makes a missing recording a named failure (verify/http.py).
VERIFY_ECFR_DATE pins the eCFR point-in-time date to the committed recording
of 2026-09-14 (first-of-month 2026-09-01), so a month rollover cannot change
which URL a golden entry asks for. setdefault: a caller may override either.
"""
import os

os.environ.setdefault("VERIFY_OFFLINE", "1")
os.environ.setdefault("VERIFY_ECFR_DATE", "2026-09-01")
