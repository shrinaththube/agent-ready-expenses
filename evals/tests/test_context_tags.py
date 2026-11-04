import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "context_tags.py"


def tags(*files):
    return subprocess.run([sys.executable, str(SCRIPT)], input="\n".join(files), capture_output=True, text=True).stdout.strip()


def test_policy_agents_maps_to_policy_and_go():
    assert tags("services/policy/AGENTS.md") == "tag:go,tag:policy"


def test_root_agents_runs_everything():
    assert tags("AGENTS.md") == "all"


def test_unrelated_change_runs_nothing():
    assert tags("docs/playbooks/working-with-agents.md") == "none"


def test_union_of_tags():
    assert tags("apps/dashboard/AGENTS.md", ".claude/skills/upgrade-dependency/SKILL.md") == "tag:deps,tag:typescript"
