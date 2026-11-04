import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checks import scan  # noqa: E402


def diff(path, *lines):
    body = "".join(f"+{ln}\n" for ln in lines)
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1,0 +1,{len(lines)} @@\n{body}"


def kinds(d, **kw):
    return {v.kind for v in scan(d, **kw)}


def test_float_money_go_ts_py():
    assert kinds(diff("services/policy/x.go", "var total float64 = 1.5")) == {"float_money"}
    assert kinds(diff("apps/dashboard/src/x.ts", "const a = parseFloat(amount)")) == {"float_money"}
    assert kinds(diff("services/receipts/app/x.py", "usd = float(amount_minor) / rate")) == {"float_money"}
    assert kinds(diff("apps/dashboard/src/x.ts", "label.toFixed(2) // price")) == set()  # comment only
    assert kinds(diff("apps/dashboard/src/x.ts", "const price = x.toFixed(2)")) == {"float_money"}


def test_confidence_float_is_fine():
    assert kinds(diff("services/receipts/app/p.py", "confidence = float(total_signals)")) == set()
    assert kinds(diff("services/receipts/app/p.py", "n = float(x)")) == set()  # not money-ish


def test_policy_logic_in_handler():
    assert kinds(diff("services/policy/api/server.go", "if e.BaseAmount.AmountMinor > 50000 {")) == {"policy_outside_registry"}
    assert kinds(diff("services/policy/api/server.go", 'if e.Category == "meals" {')) == {"policy_outside_registry"}
    assert kinds(diff("services/policy/policy/rules/new.go", "if x.BaseAmount.AmountMinor > r.Max {")) == set()
    assert kinds(diff("services/policy/api/api_test.go", "if e.Category == meals {")) == set()


def test_submitted_write():
    assert kinds(diff("services/policy/api/server.go", "orig.Description = patch.Description")) == {"submitted_write"}
    assert kinds(diff("services/policy/api/server.go", "e.Status = contracts.ExpenseStatusApproved")) == {"submitted_write"}
    assert kinds(diff("services/policy/api/server.go", "rev.Description = patch.Description")) == set()
    assert kinds(diff("services/policy/workflow/workflow.go", "e.Status = to")) == set()


def test_forbidden_and_max_files():
    d = diff("services/receipts/legacy/fx_v1.py", "x = 1")
    assert kinds(d, forbidden=["services/receipts/legacy/"]) == {"forbidden_path"}
    two = diff("a.py", "x=1") + diff("b.py", "y=2")
    assert kinds(two, max_files=1) == {"too_many_files"}


def test_nil_checks_are_not_policy_logic():
    assert kinds(diff("services/policy/api/server.go", "if p.Category != nil {")) == set()
