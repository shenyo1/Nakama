"""Helpers for deploy/auto-repair.sh. Reads a /sources/health JSON on stdin
and prints a single line: <down_count>|<comma-separated names>|<total>.

With --digest: prints healthy|degraded|down.
"""
import json
import sys


def parse_digest(d):
    summary = d.get("summary", {})
    return (
        summary.get("healthy", 0),
        summary.get("degraded", 0),
        summary.get("down", 0),
    )


def parse_down(d):
    summary = d.get("summary", {})
    open_bk = d.get("auto_repair", {}).get("open_breakers", [])
    down_sources = [
        s["name"] for s in d.get("sources", []) if s.get("status") == "down"
    ]
    total_down = summary.get("down", 0) + len(open_bk)
    names = ",".join(sorted(set(down_sources + open_bk)))
    total = summary.get("total", 0)
    return f"{total_down}|{names}|{total}"


try:
    d = json.load(sys.stdin)
except Exception as e:
    if "--digest" in sys.argv:
        print("0|0|0")
    else:
        print(f"0|parse-error:{e}|0")
    sys.exit(0)

# Response is wrapped: {ok, source, data: {...summary, sources, auto_repair...}}
if "data" in d and isinstance(d["data"], dict):
    d = d["data"]


def parse_digest(d):
    summary = d.get("summary", {})
    return (
        summary.get("healthy", 0),
        summary.get("degraded", 0),
        summary.get("down", 0),
    )


def parse_down(d):
    summary = d.get("summary", {})
    open_bk = d.get("auto_repair", {}).get("open_breakers", [])
    down_sources = [
        s["name"] for s in d.get("sources", []) if s.get("status") == "down"
    ]
    total_down = summary.get("down", 0) + len(open_bk)
    names = ",".join(sorted(set(down_sources + open_bk)))
    total = summary.get("total", 0)
    return f"{total_down}|{names}|{total}"


if "--digest" in sys.argv:
    h, deg, dn = parse_digest(d)
    print(f"{h}|{deg}|{dn}")
else:
    print(parse_down(d))