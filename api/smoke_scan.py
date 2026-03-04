import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _request_json(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    data = None
    headers = {"X-API-Key": api_key}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentra API smoke scan runner")
    parser.add_argument("--base-url", default="http://localhost:8000", help="FastAPI base URL")
    parser.add_argument("--api-key", required=True, help="SENTRA_API_KEY value")
    parser.add_argument("--target", default="example.com", help="Scan target")
    parser.add_argument(
        "--scan-type",
        default="quick",
        choices=["quick", "ports", "web", "full"],
        help="Scan type",
    )
    parser.add_argument("--timeout", type=int, default=240, help="Max seconds to wait")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Poll interval seconds")
    args = parser.parse_args()

    scans_url = f"{args.base_url.rstrip('/')}/api/v1/scans"

    try:
        created = _request_json(
            "POST",
            scans_url,
            args.api_key,
            {"target": args.target, "scan_type": args.scan_type},
        )
    except urllib.error.HTTPError as exc:
        print(f"[FAIL] create scan HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')}")
        return 1
    except Exception as exc:
        print(f"[FAIL] create scan error: {exc}")
        return 1

    scan_id = created.get("scan_id")
    if not scan_id:
        print(f"[FAIL] missing scan_id in response: {created}")
        return 1

    print(f"[OK] created scan_id={scan_id}")

    scan_url = f"{scans_url}/{scan_id}"
    deadline = time.time() + args.timeout

    while time.time() < deadline:
        try:
            scan = _request_json("GET", scan_url, args.api_key)
        except Exception as exc:
            print(f"[FAIL] polling error: {exc}")
            return 1

        status = scan.get("status")
        print(f"[INFO] status={status}")
        if status == "completed":
            findings = scan.get("findings") or []
            summary = scan.get("summary")
            print(f"[OK] completed findings={len(findings)} summary={bool(summary)}")
            print(json.dumps(scan, indent=2))
            return 0

        if status == "failed":
            print("[FAIL] scan failed")
            print(json.dumps(scan, indent=2))
            return 1

        time.sleep(args.poll_interval)

    print(f"[FAIL] timeout waiting for completion after {args.timeout}s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
