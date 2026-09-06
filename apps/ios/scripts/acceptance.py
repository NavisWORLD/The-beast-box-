"""Launch the installed simulator app three times, retaining its app container."""
import json
import pathlib
import subprocess
import sys
import time

udid, evidence = sys.argv[1:]
evidence = pathlib.Path(evidence)
evidence.mkdir(parents=True, exist_ok=True)

def sim(*args, check=True):
    return subprocess.run(['xcrun', 'simctl', *args], check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

container = pathlib.Path(sim('get_app_container', udid, 'dev.beastbox.mobile', 'data'))
receipt_path = container / 'Documents/acceptance.json'
receipts = []
for index, model in enumerate(('A', 'B', 'A')):
    sim('terminate', udid, 'dev.beastbox.mobile', check=False)
    receipt_path.unlink(missing_ok=True)
    sim('launch', udid, 'dev.beastbox.mobile', '--acceptance', model)
    for _ in range(120):
        if receipt_path.exists():
            break
        time.sleep(1)
    receipt = json.loads(receipt_path.read_text())
    (evidence / f'launch-{index + 1}-{model}.json').write_text(json.dumps(receipt, indent=2))
    assert receipt['ok'], receipt
    assert receipt['after']['turn'] == index + 1, receipt
    assert receipt['result']['model']['model'] == f'fixture-{model}'
    assert receipt['after']['valid']
    if receipts:
        assert receipt['before'] == receipts[-1]['after'], 'restart changed retained checkpoint'
    receipts.append(receipt)
assert len({r['after']['system_id'] for r in receipts}) == 1
(evidence / 'acceptance.json').write_text(json.dumps({
    'passed': True, 'platform': 'ios-simulator', 'runtime': 'CPython DurableRuntime',
    'fixture': True, 'process_launches': 3, 'models': ['A', 'B', 'A'],
    'physical_device': False, 'signed_distribution': False}, indent=2))
