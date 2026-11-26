"""Check the four public HTTP cases without displaying credentials."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--key-file", help="Local ignored env file; alternatively set AGENT_API_KEY")
    parser.add_argument("--out", help="Save a credential-free JSON report")
    args = parser.parse_args()
    key = os.getenv("AGENT_API_KEY", "")
    if args.key_file:
        values = dict(line.split("=", 1) for line in Path(args.key_file).read_text(encoding="utf-8").splitlines()
                      if "=" in line and not line.lstrip().startswith("#"))
        key = values.get("AGENT_API_KEY", "")
    if not key:
        parser.error("Set AGENT_API_KEY or provide --key-file; do not paste the key in command arguments")
    results = []
    cases = [("GET", "/health", False, 200), ("GET", "/ready", False, 200),
             ("POST", "/ask", False, 401), ("POST", "/ask", True, 200)]
    for method, path, authenticated, expected in cases:
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["X-API-Key"] = key
        request = Request(args.url.rstrip("/") + path, method=method, headers=headers,
                          data=b'{"question":"Hello"}' if method == "POST" else None)
        try:
            with urlopen(request, timeout=60) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
        except (URLError, TimeoutError):
            status = 0
        results.append({"method": method, "path": path, "with_key": authenticated,
                        "expected": expected, "status": status, "passed": status == expected})
        print(f"{method} {path} {'with key' if authenticated else 'without key'}: {status} (expected {expected})")
    passed = all(result["passed"] for result in results)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "url": args.url.rstrip("/"),
              "passed": passed, "checks": results}
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS 4/4" if passed else "FAIL: see status codes above")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
