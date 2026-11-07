import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "digitalocean.py"
spec = importlib.util.spec_from_file_location("do_adapter", SCRIPT)
do = importlib.util.module_from_spec(spec)
spec.loader.exec_module(do)

VMID = "deaa1e13-4ef6-4cf8-aa21-35e174906247"


class FakeAPI:
    def __init__(self, existing=None, fail_create=False):
        self.existing = existing
        self.fail_create = fail_create
        self.calls = []

    def request(self, method, path, data=None):
        self.calls.append((method, path, data))
        if method == "GET" and path.startswith("/droplets?"):
            return {"droplets": [self.existing] if self.existing else [],
                    "links": {}}
        if method == "POST" and path == "/droplets":
            if self.fail_create:
                raise do.ProviderError("API outcome uncertain")
            return {"droplet": {"id": 123}}
        if method == "DELETE":
            return {}
        if method == "POST" and path.endswith("/actions"):
            return {"action": {"id": 444}}
        raise AssertionError((method, path))


def payload():
    return {"virtualmachineid": VMID,
            "virtualmachinename": "i-2-VM",
            "externaldetails": {"extension": {"region": "sfo3", "size": "s-1vcpu-1gb",
                                               "image": "ubuntu-24-04-x64", "vpc_uuid": "vpc-test"}}}


def droplet(status="active", name="vm-name"):
    return {"id": 123, "name": name, "status": status,
            "region": {"slug": "sfo3"}, "tags": [do.MANAGED_TAG, do.vm_tag(VMID)]}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.dict(os.environ, {"SKYMOON_DO_STATE_DIR": self.tmp.name,
                                           "SKYMOON_DO_ALLOW_CREATE": "true"})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_prepare_patch(self):
        self.assertEqual(do.dispatch("prepare", payload(), FakeAPI()),
                         {"details": {"skymoon_do_tag": do.vm_tag(VMID)}})

    def test_create_requires_explicit_operator_opt_in(self):
        api = FakeAPI()
        with patch.dict(os.environ, {"SKYMOON_DO_ALLOW_CREATE": "false"}):
            with self.assertRaisesRegex(do.ProviderError, "creation is disabled"):
                do.dispatch("create", payload(), api)
        self.assertFalse(any(x[0] == "POST" for x in api.calls))

    def test_create_rejects_unapproved_size(self):
        api = FakeAPI()
        data = payload()
        data["externaldetails"]["extension"]["size"] = "s-8vcpu-16gb"
        with self.assertRaisesRegex(do.ProviderError, "not permitted"):
            do.dispatch("create", data, api)
        self.assertFalse(any(x[0] == "POST" for x in api.calls))

    def test_create_uses_vpc_region_size_and_tags(self):
        api = FakeAPI()
        result = do.dispatch("create", payload(), api)
        self.assertEqual(result["provider_id"], 123)
        post = api.calls[-1]
        self.assertEqual(post[:2], ("POST", "/droplets"))
        self.assertEqual(post[2]["vpc_uuid"], "vpc-test")
        self.assertEqual(post[2]["region"], "sfo3")
        self.assertIn(do.vm_tag(VMID), post[2]["tags"])

    def test_existing_vm_skips_create(self):
        api = FakeAPI(existing=droplet())
        self.assertEqual(do.dispatch("create", payload(), api)["provider_id"], 123)
        self.assertFalse(any(x[0] == "POST" for x in api.calls))

    def test_unknown_create_outcome_is_not_retried(self):
        api = FakeAPI(fail_create=True)
        with self.assertRaises(do.ProviderError):
            do.dispatch("create", payload(), api)
        with self.assertRaisesRegex(do.ProviderError, "unresolved"):
            do.dispatch("create", payload(), api)
        self.assertEqual(sum(1 for method, _, _ in api.calls if method == "POST"), 1)

    def test_delete_refuses_ambiguous_create(self):
        api = FakeAPI(fail_create=True)
        with self.assertRaises(do.ProviderError):
            do.dispatch("create", payload(), api)
        with self.assertRaisesRegex(do.ProviderError, "cannot confirm safe deletion"):
            do.dispatch("delete", payload(), api)

    def test_delete_after_accepted_create_records_tombstone(self):
        api = FakeAPI()
        do.dispatch("create", payload(), api)
        api.existing = droplet()
        self.assertEqual(do.dispatch("delete", payload(), api)["status"], "success")
        self.assertEqual(do.dispatch("delete", payload(), FakeAPI())["status"], "success")

    def test_status_maps_cloudstack_power_states(self):
        self.assertEqual(do.dispatch("status", payload(), FakeAPI(existing=droplet("active")))["power_state"], "PowerOn")
        self.assertEqual(do.dispatch("status", payload(), FakeAPI(existing=droplet("off")))["power_state"], "PowerOff")

    def test_statuses_object_has_expected_shape(self):
        result = do.dispatch("statuses", payload(), FakeAPI(existing=droplet()))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["power_state"], {"vm-name": "PowerOn"})

    def test_refuse_foreign_droplet(self):
        wrong = droplet()
        wrong["tags"] = ["someone-else"]
        api = FakeAPI(existing=wrong)
        with self.assertRaisesRegex(do.ProviderError, "identity tags"):
            do.dispatch("delete", payload(), api)
        self.assertFalse(any(x[0] == "DELETE" for x in api.calls))

    def test_delete_missing_is_noop(self):
        api = FakeAPI()
        self.assertIn("success", do.dispatch("delete", payload(), api).values())
        self.assertFalse(any(x[0] == "DELETE" for x in api.calls))

    def test_stop_action(self):
        api = FakeAPI(existing=droplet())
        do.dispatch("stop", payload(), api)
        self.assertEqual(api.calls[-1], ("POST", "/droplets/123/actions", {"type": "shutdown"}))

    def test_reject_existing_vm_wrong_region(self):
        existing = droplet()
        existing["region"]["slug"] = "nyc3"
        with self.assertRaisesRegex(do.ProviderError, "wrong DigitalOcean region"):
            do.dispatch("create", payload(), FakeAPI(existing=existing))

    def test_non_dns_name_is_rejected(self):
        data = payload()
        data["virtualmachinename"] = "invalid/name"
        with self.assertRaisesRegex(do.ProviderError, "not a valid Droplet DNS name"):
            do.dispatch("create", data, FakeAPI())

    def test_reject_invalid_vm_id(self):
        data = payload()
        data["virtualmachineid"] = "../../../etc/passwd"
        with self.assertRaisesRegex(do.ProviderError, "invalid CloudStack VM UUID"):
            do.dispatch("status", data, FakeAPI())


if __name__ == "__main__":
    unittest.main()
