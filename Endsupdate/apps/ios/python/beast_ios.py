"""iOS JSON boundary; every operation opens the actual durable Python store."""
import json
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider


def dispatch(root, request_json):
    try:
        request = json.loads(request_json)
        if not isinstance(request, dict) or request.get('schema') != 'beast-ios-v1':
            raise ValueError('expected beast-ios-v1 object')
        model = request.get('model', 'A')
        if model not in ('A', 'B'):
            raise ValueError('only reference fixtures A and B are bundled')
        runtime = DurableRuntime(Path(root), ReferenceTextProvider(prefix='fixture-' + model))
        try:
            before = runtime.inspect()
            action = request.get('action')
            if action == 'inspect':
                result = before
            elif action == 'send':
                result = runtime.respond(request.get('text'))
            else:
                raise ValueError('unsupported action')
            return json.dumps({'schema': 'beast-ios-receipt-v1', 'ok': True,
                               'before': before, 'after': runtime.inspect(), 'result': result,
                               'model': model, 'fixture': True})
        finally:
            runtime.memory.close()
    except Exception as error:
        return json.dumps({'schema': 'beast-ios-receipt-v1', 'ok': False,
                           'error': str(error)})
