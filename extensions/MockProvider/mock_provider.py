#!/usr/bin/env python3
"""Offline External VM executable for SkyMoon integration development.

Usage: mock_provider.py <action> <json-payload-file> <timeout-seconds>
No API calls, networking, credentials or billable resources are used.
"""
import fcntl
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
ACTIONS = {"prepare", "create", "start", "stop", "reboot", "delete", "status", "statuses"}


class MockError(Exception):
    pass


def vm_id(payload):
    vm = payload.get("virtualmachineid") or payload.get("cloudstack.vm.details", {}).get("uuid")
    if not isinstance(vm, str) or not UUID_PATTERN.fullmatch(vm):
        raise MockError("A valid CloudStack VM UUID is required")
    return vm.lower()


def vm_name(payload, identity):
    name = payload.get("virtualmachinename") or payload.get("cloudstack.vm.details", {}).get("name") or identity
    if not isinstance(name, str) or len(name) > 120 or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", name):
        raise MockError("Invalid CloudStack VM name")
    return name


@contextmanager
def locked_state():
    directory = Path(os.environ.get("SKYMOON_MOCK_PROVIDER_STATE_DIR", "/tmp/skymoon-mock-provider"))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not directory.is_dir():
        raise MockError("Mock provider state location is not a directory")
    lock = directory / ".lock"
    with lock.open("a+b") as handle:
        os.chmod(lock, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield directory
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_record(directory, identity):
    path = directory / (identity + ".json")
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf8"))
        if record.get("id") != identity or record.get("power_state") not in {"PowerOn", "PowerOff"}:
            raise ValueError("invalid VM state")
        return record
    except (OSError, ValueError, AttributeError) as exc:
        raise MockError("Corrupt mock VM state; refusing to overwrite") from exc


def write_record(directory, identity, record):
    path = directory / (identity + ".json")
    fd, filename = tempfile.mkstemp(prefix=".vm-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf8") as handle:
            os.chmod(filename, 0o600)
            json.dump(record, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(filename, path)
    finally:
        if os.path.exists(filename):
            os.unlink(filename)


def dispatch(action, payload):
    if action not in ACTIONS:
        raise MockError("Unsupported external operation")
    if action == "prepare":
        identity = vm_id(payload)
        return {"details": {"skymoon_mock_id": identity}}
    with locked_state() as directory:
        if action == "statuses":
            states = {}
            for path in directory.glob("*.json"):
                identity = path.stem
                if not UUID_PATTERN.fullmatch(identity):
                    continue
                vm = read_record(directory, identity)
                if vm["name"] in states:
                    raise MockError("Duplicate VM names in mock inventory")
                states[vm["name"]] = vm["power_state"]
            return {"status": "success", "power_state": states}
        identity = vm_id(payload)
        record = read_record(directory, identity)
        if action == "status":
            return {"status": "success", "power_state": record["power_state"] if record else "PowerUnknown"}
        if action == "create":
            name = vm_name(payload, identity)
            if record and record["name"] != name:
                raise MockError("Existing VM has a different name")
            if record is None:
                record = {"id": identity, "name": name, "power_state": "PowerOn"}
                write_record(directory, identity, record)
            return {"status": "success", "message": "Mock VM exists"}
        if action == "delete":
            if record:
                (directory / (identity + ".json")).unlink()
            return {"status": "success", "message": "Mock VM deleted"}
        if not record:
            raise MockError("Mock VM not found")
        if action == "stop":
            record["power_state"] = "PowerOff"
        else:
            record["power_state"] = "PowerOn"
        write_record(directory, identity, record)
        return {"status": "success", "message": "Mock VM action completed"}


def main(argv):
    try:
        if len(argv) != 4:
            raise MockError("Expected action, payload-file and timeout")
        _, action, payload_file, timeout = argv
        if not timeout.isdigit() or int(timeout) < 1:
            raise MockError("Invalid timeout")
        with open(payload_file, encoding="utf8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise MockError("Expected JSON object payload")
        print(json.dumps(dispatch(action, payload), separators=(",", ":")))
        return 0
    except (MockError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
