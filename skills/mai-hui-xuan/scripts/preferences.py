#!/usr/bin/env python3
"""Explicit, local preference storage. Python standard library only."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile

FIELDS = {"budget_yuan", "likes", "avoid", "must_keep", "low_calorie"}


def validate(data):
    if not isinstance(data, dict) or set(data) - FIELDS:
        raise ValueError("仅允许 budget_yuan、likes、avoid、must_keep、low_calorie")
    for key, value in data.items():
        if key in ("likes", "avoid", "must_keep"):
            if not isinstance(value, list) or len(value) > 30 or any(not isinstance(x, str) or not x.strip() or len(x) > 100 for x in value):
                raise ValueError(key + " 必须是最多 30 条简短字符串列表")
        elif key == "budget_yuan":
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError("预算必须为有限正数")
        elif type(value) is not bool:
            raise ValueError("low_calorie 必须是布尔值")
    return data


def read(path):
    return validate(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else {}


def save(path, data):
    validate(data)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=".prefs-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    sub.add_parser("clear")
    setter = sub.add_parser("set")
    setter.add_argument("--json", required=True)
    unset = sub.add_parser("unset")
    unset.add_argument("field", choices=sorted(FIELDS))
    args = parser.parse_args()
    path = Path(os.environ.get("MAI_HUI_XUAN_HOME", str(Path.home() / ".mai-hui-xuan"))).expanduser() / "preferences.json"
    try:
        if args.command == "clear":
            if path.exists():
                path.unlink()
            data = {}
        else:
            data = read(path)
            if args.command == "set":
                data.update(validate(json.loads(args.json)))
                save(path, data)
            elif args.command == "unset":
                data.pop(args.field, None)
                save(path, data)
        print(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError) as exc:
        print("偏好操作失败：" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
