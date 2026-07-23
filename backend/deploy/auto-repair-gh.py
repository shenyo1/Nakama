"""Helper for deploy/auto-repair.sh — creates a GitHub issue for a source outage.

Usage:
    python3 auto-repair-gh.py <source> <down_names> <down_count>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: auto-repair-gh.py <source> <down_names> <down_count>", file=sys.stderr)
        return 1
    source = sys.argv[1]
    down_names = sys.argv[2]
    try:
        down_count = int(sys.argv[3])
    except ValueError:
        down_count = 0

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    try:
        from app.sources.github_issues import create_issue
    except Exception as e:
        print(f"import-error: {e}", file=sys.stderr)
        return 1

    res = create_issue(
        source=source,
        error_summary=f"Co-detected with: {down_names}",
        probe_items=down_count,
        threshold=5,
        cooldown_active=False,
    )
    print(f"{res.get('action')}: {res.get('url') or res.get('error')}")
    return 0 if res.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())