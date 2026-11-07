#!/usr/bin/env python3
"""DigitalOcean External hypervisor adapter for SkyMoon Cloud.

Invoked by CloudStack's ExternalPathPayloadProvisioner as:
    digitalocean.py <action> <json-payload-path> <timeout-seconds>
The stdout protocol intentionally follows the existing External scripts. This
adapter is experimental and does not claim provider-managed IP/storage support.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.digitalocean.com/v2"
MANAGED_TAG = "skymoon-managed"
UUID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]{3,95}$")


class ProviderError(Exception):
    pass


class API:
    def __init__(self, token, timeout=30):
        if not token:
            raise ProviderError("DigitalOcean token not configured")
        self.token = token
        self.timeout = max(1, min(int(timeout), 120))

    def request(self, method, path, data=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ProviderError("Invalid DigitalOcean API path")
        request = urllib.request.Request(
            BASE_URL + path,
            data=(json.dumps(data).encode("utf-8") if data is not None else None),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            # Do not forward HTTP response bodies: they may include customer data.
            raise ProviderError(f"DigitalOcean API returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError("DigitalOcean API request failed or timed out; outcome may be uncertain") from None


def nested(data, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def config(payload, key):
    # Prefer extension/host-scoped settings; do not accept customer-selected provider IDs.
    for scope in ("host", "extension"):
        value = nested(payload, "externaldetails", scope, key)
        if value is not None and value != "":
            return value
    return None


def vm_identity(payload):
    vmid = payload.get("virtualmachineid") or nested(payload, "cloudstack.vm.details", "uuid")
    if not isinstance(vmid, str) or not UUID_RE.fullmatch(vmid):
        raise ProviderError("Missing or invalid CloudStack VM UUID")
    return vmid.lower()


def vm_tag(vmid):
    return "skymoon-vm-" + vmid


def safe_name(payload, vmid):
    # Preserve CloudStack's internal instance name for the bulk statuses map.
    # Droplet identity is enforced separately by the unique SkyMoon VM tag.
    name = str(payload.get("virtualmachinename") or
               nested(payload, "cloudstack.vm.details", "name") or "")
    if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,61}[A-Za-z0-9])?", name):
        return name
    # Non-DNS names are not silently passed to the provider.
    raise ProviderError("CloudStack internal VM name is not a valid Droplet DNS name")


def list_tagged(api, tag):
    result = []
    page = 1
    for _ in range(100):
        query = urllib.parse.urlencode({"tag_name": tag, "per_page": 200, "page": page})
        body = api.request("GET", f"/droplets?{query}")
        droplets = body.get("droplets")
        if not isinstance(droplets, list):
            raise ProviderError("Malformed Droplet list response")
        result.extend(droplets)
        next_url = nested(body, "links", "pages", "next")
        if not next_url:
            return result
        next_page = urllib.parse.parse_qs(urllib.parse.urlparse(next_url).query).get("page")
        try:
            new_page = int(next_page[0])
        except (TypeError, ValueError, IndexError):
            raise ProviderError("Invalid API pagination response") from None
        if new_page <= page:
            raise ProviderError("Non-progressing API pagination")
        page = new_page
    raise ProviderError("Droplet query exceeded pagination limit")


def find_vm(api, vmid):
    matches = list_tagged(api, vm_tag(vmid))
    if len(matches) > 1:
        raise ProviderError("Duplicate Droplets have the same SkyMoon VM identity; refusing operation")
    if not matches:
        return None
    droplet = matches[0]
    tags = droplet.get("tags", [])
    if vm_tag(vmid) not in tags or MANAGED_TAG not in tags:
        raise ProviderError("Droplet identity tags do not match the SkyMoon VM")
    return droplet


def power(droplet):
    status = droplet.get("status", "")
    return "PowerOn" if status == "active" else "PowerOff" if status == "off" else "PowerUnknown"


def state_file(vmid):
    directory = Path(os.environ.get("SKYMOON_DO_STATE_DIR", "/var/lib/skymoon-providers/digitalocean"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory / (vm_tag(vmid) + ".json")


def record_intent(path, vmid):
    try:
        with path.open("x", encoding="utf-8") as fp:
            os.chmod(path, 0o600)
            json.dump({"vmid": vmid, "create_attempted": True}, fp)
            fp.flush()
            os.fsync(fp.fileno())
    except FileExistsError:
        raise ProviderError("Prior VM creation attempt is unresolved; reconcile the provider before retrying") from None


def dispatch(action, payload, api):
    if action == "prepare":
        vmid = vm_identity(payload)
        return {"details": {"skymoon_do_tag": vm_tag(vmid)}}

    if action == "statuses":
        region = config(payload, "region") or os.environ.get("SKYMOON_DO_REGION")
        output = {}
        for droplet in list_tagged(api, MANAGED_TAG):
            if region and nested(droplet, "region", "slug") != region:
                continue
            tags = droplet.get("tags", [])
            if not any(t.startswith("skymoon-vm-") for t in tags):
                continue
            output[droplet.get("name", str(droplet.get("id", "unknown")))] = power(droplet)
        return {"status": "success", "power_state": output}

    vmid = vm_identity(payload)
    if action == "create":
        size = config(payload, "size") or os.environ.get("SKYMOON_DO_SIZE")
        image = config(payload, "image") or os.environ.get("SKYMOON_DO_IMAGE")
        region = config(payload, "region") or os.environ.get("SKYMOON_DO_REGION")
        vpc = config(payload, "vpc_uuid") or os.environ.get("SKYMOON_DO_VPC_UUID")
        if not all((size, image, region, vpc)):
            raise ProviderError("Missing explicit region, size, image or VPC UUID for DigitalOcean VM")
        existing = find_vm(api, vmid)
        if existing:
            existing_region = nested(existing, "region", "slug")
            existing_size = nested(existing, "size", "slug")
            if existing_region and existing_region != region:
                raise ProviderError("Existing VM is in the wrong DigitalOcean region")
            if existing_size and existing_size != size:
                raise ProviderError("Existing VM has the wrong DigitalOcean size")
            return {"status": "success", "message": "Existing VM found", "provider_id": existing["id"]}
        # Durable local intent prevents blindly repeating POST after an unknown outcome.
        marker = state_file(vmid)
        record_intent(marker, vmid)
        args = {"name": safe_name(payload, vmid), "region": region,
                "size": size, "image": image, "vpc_uuid": vpc,
                "tags": [MANAGED_TAG, vm_tag(vmid)]}
        ssh_keys = config(payload, "ssh_keys")
        if ssh_keys:
            args["ssh_keys"] = [x.strip() for x in str(ssh_keys).split(",") if x.strip()]
        body = api.request("POST", "/droplets", args)
        droplet = body.get("droplet")
        if not isinstance(droplet, dict) or not droplet.get("id"):
            raise ProviderError("Droplet creation response missing provider ID; reconcile before retry")
        return {"status": "success", "provider_id": droplet["id"]}

    droplet = find_vm(api, vmid)
    if action == "status":
        return {"status": "success", "power_state": power(droplet) if droplet else "PowerUnknown"}
    if action == "delete":
        if droplet:
            api.request("DELETE", f"/droplets/{int(droplet['id'])}")
        # Do not clear a creation marker for a missing VM: a delayed POST may still succeed.
        return {"status": "success", "message": "Delete requested or VM already absent"}
    if action == "stop" and not droplet:
        return {"status": "success", "message": "VM absent"}
    if action in ("start", "stop", "reboot"):
        if not droplet:
            raise ProviderError("SkyMoon VM not found in provider account")
        if action == "start" and power(droplet) == "PowerOn":
            return {"status": "success", "message": "Already running"}
        if action == "stop" and power(droplet) == "PowerOff":
            return {"status": "success", "message": "Already stopped"}
        kind = {"start": "power_on", "stop": "shutdown", "reboot": "reboot"}[action]
        api.request("POST", f"/droplets/{int(droplet['id'])}/actions", {"type": kind})
        return {"status": "success", "message": f"{action} requested"}
    raise ProviderError(f"Unsupported DigitalOcean extension action: {action}")


def main(argv):
    if len(argv) != 4:
        print(json.dumps({"status": "error", "error": "Expected action, payload file and timeout"}))
        return 2
    action, payload_file, timeout = argv[1:]
    try:
        if action not in {"prepare", "create", "start", "stop", "reboot", "delete", "status", "statuses"}:
            raise ProviderError("Unsupported extension action")
        with open(payload_file, encoding="utf-8") as fp:
            payload = json.load(fp)
        token = os.environ.get("SKYMOON_DEV_DO_TOKEN") or config(payload, "token")
        api = None if action == "prepare" else API(token, int(timeout))
        print(json.dumps(dispatch(action, payload, api), separators=(",", ":")))
        return 0
    except (ProviderError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
