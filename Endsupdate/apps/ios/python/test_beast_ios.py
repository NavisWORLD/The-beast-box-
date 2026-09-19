"""Run with PYTHONPATH=apps/ios/python:. python -m unittest discover -s apps/ios/python."""
import json
import tempfile
import unittest
from beast_ios import dispatch


class BoundaryTests(unittest.TestCase):
    def test_reopen_swap_and_invalid_input_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as root:
            last = None
            for index, model in enumerate(('A', 'B', 'A'), 1):
                request = {'schema': 'beast-ios-v1', 'action': 'send',
                           'model': model, 'text': 'retained marker'}
                receipt = json.loads(dispatch(root, json.dumps(request)))
                self.assertTrue(receipt['ok'], receipt)
                self.assertEqual(receipt['after']['turn'], index)
                self.assertEqual(receipt['result']['model']['model'], 'fixture-' + model)
                if last:
                    self.assertEqual(receipt['before'], last['after'])
                last = receipt
            for request in ('[]', '{}', '{', json.dumps({'schema': 'beast-ios-v1', 'model': 'other'}),
                            json.dumps({'schema': 'beast-ios-v1', 'action': 'send', 'text': 3})):
                self.assertFalse(json.loads(dispatch(root, request))['ok'])
            inspection = json.loads(dispatch(root, json.dumps({'schema': 'beast-ios-v1', 'action': 'inspect'})))
            self.assertEqual(inspection['after'], last['after'])
