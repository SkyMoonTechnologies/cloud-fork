import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'mock_provider.py'
spec = importlib.util.spec_from_file_location('mock_external', SCRIPT)
provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)
VMID = 'cafebabe-0101-0202-0303-d4d4d4d4d4d4'
PAYLOAD = {'virtualmachineid': VMID, 'virtualmachinename': 'i-2-VM'}


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.environment = patch.dict(os.environ, {'SKYMOON_MOCK_PROVIDER_STATE_DIR': self.tmp.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_prepare_contract(self):
        self.assertEqual(provider.dispatch('prepare', PAYLOAD)['details']['skymoon_mock_id'], VMID)

    def test_create_and_read_power_state(self):
        provider.dispatch('create', PAYLOAD)
        self.assertEqual(provider.dispatch('status', PAYLOAD)['power_state'], 'PowerOn')
        self.assertEqual(provider.dispatch('statuses', {})['power_state'], {'i-2-VM': 'PowerOn'})

    def test_full_lifecycle(self):
        provider.dispatch('create', PAYLOAD)
        for action, expected in [('stop', 'PowerOff'), ('start', 'PowerOn'), ('reboot', 'PowerOn')]:
            provider.dispatch(action, PAYLOAD)
            self.assertEqual(provider.dispatch('status', PAYLOAD)['power_state'], expected)
        provider.dispatch('delete', PAYLOAD)
        self.assertEqual(provider.dispatch('status', PAYLOAD)['power_state'], 'PowerUnknown')

    def test_repeated_create_does_not_duplicate(self):
        provider.dispatch('create', PAYLOAD)
        provider.dispatch('create', PAYLOAD)
        self.assertEqual(len(list(Path(self.tmp.name).glob('*.json'))), 1)

    def test_wrong_name_refuses_existing_vm(self):
        provider.dispatch('create', PAYLOAD)
        with self.assertRaisesRegex(provider.MockError, 'different name'):
            provider.dispatch('create', dict(PAYLOAD, virtualmachinename='other'))

    def test_unknown_vm_start_rejected(self):
        with self.assertRaisesRegex(provider.MockError, 'not found'):
            provider.dispatch('start', PAYLOAD)

    def test_unknown_vm_status(self):
        self.assertEqual(provider.dispatch('status', PAYLOAD)['power_state'], 'PowerUnknown')

    def test_malformed_uuid_is_rejected(self):
        with self.assertRaisesRegex(provider.MockError, 'UUID'):
            provider.dispatch('create', dict(PAYLOAD, virtualmachineid='../../etc/passwd'))

    def test_corrupted_record_is_not_overwritten(self):
        (Path(self.tmp.name) / (VMID + '.json')).write_text('invalid JSON')
        with self.assertRaisesRegex(provider.MockError, 'Corrupt'):
            provider.dispatch('create', PAYLOAD)

    def test_stdout_contract(self):
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf8') as payload_file:
            json.dump(PAYLOAD, payload_file)
            payload_file.flush()
            result = subprocess.run([sys.executable, str(SCRIPT), 'create', payload_file.name, '10'],
                                    capture_output=True, text=True,
                                    env={**os.environ, 'SKYMOON_MOCK_PROVIDER_STATE_DIR': self.tmp.name})
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['status'], 'success')

    def test_bad_action_returns_nonzero_json(self):
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf8') as payload_file:
            json.dump(PAYLOAD, payload_file)
            payload_file.flush()
            result = subprocess.run([sys.executable, str(SCRIPT), 'unknown', payload_file.name, '10'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['status'], 'error')


if __name__ == '__main__':
    unittest.main()
