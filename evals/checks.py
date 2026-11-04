"""Rule-violation scanners for eval diffs.

A task can pass its hidden tests and still break a Tally rule. These checks
scan only the *added* lines of the agent's diff and record violations
separately from pass/fail:

  float_money              float types / parseFloat / toFixed near money identifiers
  policy_outside_registry  approval logic (amount/category/region comparisons) in handlers or the dashboard
  submitted_write          assigning fields of a stored expense, or setting Status outside workflow
  forbidden_path           touched a path the task forbids (legacy/, generated files, ...)
  too_many_files           more files changed than the task allows
"""
import fnmatch
import re
from dataclasses import dataclass


@dataclass
class Violation:
    kind: str
    where: str
    text: str

    def as_dict(self):
        return {"kind": self.kind, "where": self.where, "text": self.text[:160]}


MONEYISH = re.compile(r"amount|total|price|money|cost|minor|cents|usd|fee|reimburs|balance", re.I)
FLOATISH = re.compile(r"\bfloat(32|64)?\b|\bparseFloat\b|\.toFixed\(|\bNumber\(\s*[^)]*(amount|total|price)", re.I)
HANDLER_LOGIC = re.compile(
    r"\.(Category|Region)\s*(==|!=)(?!\s*nil\b)|AmountMinor\s*(<=|>=|<|>)\s*[\w(]|\.Weekday\(\)|"
    r"amount_minor\s*(<=|>=|<|>)\s*\d"
)
STORED_FIELD_WRITE = re.compile(
    r"\b(exp|expense|existing|orig|original|stored|e)\.(Description|Category|Date|Amount|BaseAmount|"
    r"Attendees|Region|HasReceipt|EmployeeID|ManagerID)\b\s*=[^=]"
)
STATUS_WRITE = re.compile(r"\.Status\s*=[^=]")


def is_test(path: str) -> bool:
    return bool(re.search(r"(_test\.go|/tests?/|\.test\.tsx?|(^|/)test_[^/]*\.py)", path))


def added_lines(diff: str):
    """Yield (path, line_no, text) for each added line of a unified diff."""
    path, line_no = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].removeprefix("b/") if raw[4:] != "/dev/null" else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) - 1 if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            line_no += 1
            if path:
                yield path, line_no, raw[1:]
        elif not raw.startswith("-"):
            line_no += 1


def changed_files(diff: str) -> list[str]:
    return sorted({m.group(1) for m in re.finditer(r"^\+\+\+ b/(.+)$", diff, re.M)} |
                  {m.group(1) for m in re.finditer(r"^--- a/(.+)$", diff, re.M)})


def scan(diff: str, forbidden: list[str] | None = None, max_files: int | None = None) -> list[Violation]:
    out: list[Violation] = []
    for path, n, text in added_lines(diff):
        where = f"{path}:{n}"
        code_only = text.split("//")[0] if path.endswith((".go", ".ts", ".tsx")) else text.split("#")[0]
        if "legacy/" not in path and "confidence" not in text.lower():
            if FLOATISH.search(code_only) and MONEYISH.search(code_only):
                out.append(Violation("float_money", where, text.strip()))
        if not is_test(path):
            in_handlers = path.startswith(("services/policy/api/", "services/policy/workflow/"))
            in_dashboard = path.startswith("apps/dashboard/src/")
            if (in_handlers or in_dashboard) and HANDLER_LOGIC.search(code_only):
                out.append(Violation("policy_outside_registry", where, text.strip()))
            if path.startswith("services/policy/") and "/policy/rules/" not in path:
                if STORED_FIELD_WRITE.search(code_only) or (
                    STATUS_WRITE.search(code_only) and not path.startswith(("services/policy/workflow/", "services/policy/store/"))
                ):
                    out.append(Violation("submitted_write", where, text.strip()))
    files = changed_files(diff)
    for f in files:
        for pat in forbidden or []:
            if fnmatch.fnmatch(f, pat) or f.startswith(pat.rstrip("*")):
                out.append(Violation("forbidden_path", f, f"touches {pat}"))
                break
    if max_files is not None and len(files) > max_files:
        out.append(Violation("too_many_files", "diff", f"{len(files)} files > {max_files}"))
    return out
