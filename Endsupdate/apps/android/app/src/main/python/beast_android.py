"""JSON boundary to the real Beast runtime, called on one Android worker thread."""
import json
import re
from pathlib import Path

from beastbox.durable import DurableRuntime
from beastbox.providers import LocalOllamaProvider, ReferenceTextProvider


class AndroidRuntime:
    def __init__(self, root):
        self.root = Path(root)
        self.settings = {'kind': 'reference-a', 'model': '', 'url': ''}
        self.runtime = DurableRuntime(self.root, self._provider(self.settings))

    @staticmethod
    def _provider(settings):
        kind = settings['kind']
        if kind in ('reference-a', 'reference-b'):
            label = kind[-1].upper()
            return ReferenceTextProvider(prefix=f'Beast deterministic fixture {label}')
        if kind != 'ollama':
            raise ValueError('Choose a reference fixture or loopback Ollama')
        model = settings['model']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}', model):
            raise ValueError('Enter an Ollama model label, without credentials')
        if len(settings['url']) > 256:
            raise ValueError('Provider URL is too long')
        # Preserve Beast core loopback, proxy and redirect protections unchanged.
        return LocalOllamaProvider(model=model, base_url=settings['url'])

    def configure(self, kind, model, url):
        settings = {'kind': kind, 'model': model.strip(), 'url': url.strip()}
        if kind in ('reference-a', 'reference-b'):
            settings.update(model='', url='')
        provider = self._provider(settings)
        self.runtime.swap_provider(provider)
        self.settings = settings
        return self.inspect()

    def inspect(self):
        return json.dumps({'schema': 'beast-android-v1', 'provider': self.settings,
                           'inspection': self.runtime.inspect()}, sort_keys=True)

    def send(self, text):
        result = self.runtime.respond(text)
        return json.dumps({'schema': 'beast-android-v1', 'response': result['response'],
                           'memory_hits': result['memory_hits'], 'provider': self.settings,
                           'inspection': self.runtime.inspect()}, sort_keys=True)

    def restart(self):
        provider = self._provider(self.settings)
        self.runtime.close()
        self.runtime = DurableRuntime(self.root, provider)
        return self.inspect()

    def close(self):
        self.runtime.close()
