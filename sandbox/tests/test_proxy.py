import json
import subprocess
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "demo_injection.py"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proxy"))
import egress_proxy  # noqa: E402


def test_demo_blocks_injection_and_logs():
    r = subprocess.run([sys.executable, str(DEMO)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout and '"action": "blocked"' in r.stdout and "example-attacker.test" in r.stdout


def test_policy_allowlist_parsing_and_swap():
    p = egress_proxy.Policy(["# c", "a.test:443 tunnel", "b.test upstream=https"], {"PH": "REAL"})
    assert p.lookup("a.test:443")["tunnel"] and p.lookup("b.test")["upstream"] == "https"
    assert p.lookup("evil.test") is None
    assert p.swap_out(b"Bearer PH") == b"Bearer REAL" and p.swap_back(b"REAL") == b"PH"
