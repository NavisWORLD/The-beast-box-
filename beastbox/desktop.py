"""Local desktop adapter. Tk owns the UI; one worker owns all SQLite access."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
import tempfile

from .durable import DurableRuntime
from .providers import LocalOllamaProvider, ReferenceTextProvider
from .runtime_cli import backup_database


def default_data_dir() -> Path:
    return Path.home() / '.beastbox' / 'data'


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = 'reference'
    model: str = ''
    url: str = 'http://127.0.0.1:11434'

    def make_provider(self):
        if self.provider == 'reference':
            return ReferenceTextProvider(prefix=self.model or 'Reference fixture (not a trained model)')
        if self.provider != 'ollama':
            raise ValueError('Choose reference fixture or Ollama')
        if not self.model.strip() or len(self.model) > 256:
            raise ValueError('Ollama requires an explicit installed model name (1–256 characters)')
        return LocalOllamaProvider(model=self.model, base_url=self.url)


def load_settings(root: Path) -> ProviderSettings:
    path = root / 'desktop-settings.json'
    if not path.exists():
        return ProviderSettings()
    if path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError('Desktop settings must be a small regular file')
    settings = ProviderSettings(**json.loads(path.read_text(encoding='utf-8')))
    settings.make_provider()
    return settings


def save_settings(root: Path, settings: ProviderSettings) -> None:
    settings.make_provider()
    root.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.desktop-settings-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(asdict(settings), handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, root / 'desktop-settings.json')
    finally:
        Path(name).unlink(missing_ok=True)


class RuntimeWorker:
    """Create/use/close each runtime on the same serialized worker thread."""
    def __init__(self, root: Path):
        self.root = Path(root)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='beast-runtime')

    def submit(self, action, settings, value=None):
        return self.executor.submit(self._run, action, settings, value)

    def _run(self, action, settings, value):
        if action not in {'inspect', 'chat', 'backup'}:
            raise ValueError('Unsupported desktop action')
        provider = settings.make_provider()
        runtime = DurableRuntime(self.root, provider)
        try:
            if action == 'chat':
                result = runtime.respond(value)
            elif action == 'backup':
                result = backup_database(self.root, Path(value))
            else:
                result = runtime.inspect()
            save_settings(self.root, settings)
            return result
        finally:
            runtime.close()

    def close(self):
        self.executor.shutdown(wait=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def smoke(root: Path):
    """Exercise the real durable adapter without importing Tk or invoking a model."""
    settings = ProviderSettings()
    with RuntimeWorker(root) as worker:
        before = worker.submit('inspect', settings).result()
        worker.submit('chat', settings, 'Portable desktop continuity fixture').result()
    with RuntimeWorker(root) as worker:
        after = worker.submit('inspect', settings).result()
    if after['system_id'] != before['system_id'] or after['turn'] != before['turn'] + 1:
        raise RuntimeError('Desktop restart continuity check failed')
    return {'schema': 'desktop-smoke-v1', 'fixture': True, 'valid': after['valid'],
            'system_id': after['system_id'], 'turn_before': before['turn'],
            'turn_after': after['turn'], 'checkpoint_sha256': after['checkpoint_sha256']}


def run_desktop(root: Path, settings: ProviderSettings) -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, ttk
    except ImportError as exc:
        raise RuntimeError('Tk is unavailable. Install Python 3.10–3.12 with Tk support, or use --smoke / the runtime CLI.') from exc
    try:
        window = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError('Cannot open desktop display. Use a graphical session, or --smoke for headless verification.') from exc
    window.title('Beast Box — durable local runtime')
    window.geometry('900x700')
    window.minsize(650, 450)
    worker = RuntimeWorker(root)
    pending = None
    closing = False
    provider = tk.StringVar(value=settings.provider)
    model = tk.StringVar(value=settings.model)
    url = tk.StringVar(value=settings.url)
    status = tk.StringVar(value='Ready')
    frame = ttk.Frame(window, padding=12)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Beast Box', font=('', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text=f'Durable data: {root}', wraplength=850).pack(anchor='w')
    ttk.Label(frame, text='Reference is a deterministic fixture. Ollama requires your installed model.').pack(anchor='w', pady=(4, 10))
    controls = ttk.Frame(frame)
    controls.pack(fill='x')
    ttk.Label(controls, text='Provider').grid(row=0, column=0, sticky='w')
    provider_box = ttk.Combobox(controls, textvariable=provider, values=('reference', 'ollama'), state='readonly', width=12)
    provider_box.grid(row=1, column=0, padx=(0, 8))
    ttk.Label(controls, text='Model name (required for Ollama)').grid(row=0, column=1, sticky='w')
    ttk.Entry(controls, textvariable=model).grid(row=1, column=1, sticky='ew', padx=(0, 8))
    ttk.Label(controls, text='Loopback Ollama URL').grid(row=0, column=2, sticky='w')
    ttk.Entry(controls, textvariable=url, width=30).grid(row=1, column=2, sticky='ew')
    controls.columnconfigure(1, weight=1)
    transcript = scrolledtext.ScrolledText(frame, wrap='word', state='disabled', height=20)
    transcript.pack(fill='both', expand=True, pady=10)
    prompt = scrolledtext.ScrolledText(frame, wrap='word', height=4)
    prompt.pack(fill='x')
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=8)
    action_buttons = []

    def append(text):
        transcript.configure(state='normal')
        transcript.insert('end', text + '\n\n')
        transcript.see('end')
        transcript.configure(state='disabled')

    def submit(action):
        nonlocal pending
        if pending is not None:
            return
        current = ProviderSettings(provider.get(), model.get(), url.get())
        try:
            current.make_provider()
        except (ValueError, TypeError) as exc:
            messagebox.showerror('Configuration', str(exc), parent=window)
            return
        value = None
        if action == 'chat':
            value = prompt.get('1.0', 'end-1c').strip()
            if not value or len(value) > 8192:
                messagebox.showerror('Message', 'Enter 1–8192 characters.', parent=window)
                return
            append('You: ' + value)
            prompt.delete('1.0', 'end')
        elif action == 'backup':
            value = filedialog.asksaveasfilename(parent=window, title='Save new verified backup',
                                               defaultextension='.sqlite3', initialfile='beast-backup.sqlite3')
            if not value:
                return
        pending = (action, worker.submit(action, current, value))
        status.set('Working… Changes to model fields apply to the next action.')
        for button in action_buttons:
            button.configure(state='disabled')

    for label, action in [('Send', 'chat'), ('Inspect / apply model', 'inspect'), ('Backup', 'backup')]:
        button = ttk.Button(buttons, text=label, command=lambda action=action: submit(action))
        button.pack(side='left', padx=(0, 8))
        action_buttons.append(button)
    ttk.Label(frame, textvariable=status).pack(anchor='w')
    ttk.Label(frame, text='History persists locally in plaintext. Model output grants no shell or hardware permissions.').pack(anchor='w')

    def poll():
        nonlocal pending
        if pending is not None and pending[1].done():
            action, future = pending
            pending = None
            try:
                result = future.result()
                if action == 'chat':
                    append('Beast: ' + str(result.get('response', result)))
                else:
                    append(json.dumps(result, indent=2, ensure_ascii=False))
                status.set('Saved. Reference responses are fixture output.' if provider.get() == 'reference' else 'Saved.')
            except Exception as exc:
                append(f'Action failed ({type(exc).__name__}): {exc}')
                status.set('Action failed; no inference fallback was used.')
            for button in action_buttons:
                button.configure(state='normal')
        if closing and pending is None:
            worker.close()
            window.destroy()
            return
        window.after(100, poll)

    def close():
        nonlocal closing
        closing = True
        status.set('Finishing the current operation before closing…')
        for button in action_buttons:
            button.configure(state='disabled')

    window.protocol('WM_DELETE_WINDOW', close)
    append('Inspect loads the validated checkpoint. Reuse this data directory across model changes and restarts.')
    submit('inspect')
    window.after(100, poll)
    try:
        window.mainloop()
    finally:
        worker.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Beast Box desktop over DurableRuntime')
    parser.add_argument('--data-dir', type=Path, default=default_data_dir())
    parser.add_argument('--provider', choices=('reference', 'ollama'))
    parser.add_argument('--model')
    parser.add_argument('--url')
    parser.add_argument('--smoke', action='store_true', help='headless reference-fixture continuity check; commits one turn')
    args = parser.parse_args(argv)
    root = args.data_dir.expanduser().absolute()
    try:
        if args.smoke:
            print(json.dumps(smoke(root)))
        else:
            saved = load_settings(root)
            settings = ProviderSettings(args.provider or saved.provider,
                                        args.model if args.model is not None else saved.model,
                                        args.url or saved.url)
            settings.make_provider()
            run_desktop(root, settings)
        return 0
    except Exception as exc:
        print(f'Beast Box: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
