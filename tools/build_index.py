"""Validate free config packages and build the static GitHub browse index."""
import argparse
import json
import re
from pathlib import Path
from config_packages import validate_config

MAX_BYTES = 4 * 1024 * 1024

def build(root):
    entries = []
    for path in sorted((root / 'configs').glob('*.json')):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', path.stem):
            raise ValueError(f'Invalid config filename: {path.name}')
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise ValueError(f'Config file exceeds limits: {path.name}')
        package = validate_config(json.loads(path.read_text(encoding='utf-8')))
        config = package['config']
        entries.append(dict(id=path.stem, name=config['name'], game=config['game'], author=package['author'], input_mode=config.get('input_mode', 'Hybrid'), calibrated=bool(config.get('calibration', {}).get('measured', False))))
    if len(entries) > 10000:
        raise ValueError('Library exceeds 10,000 configs. Split into separate repositories.')
    result = json.dumps(dict(schema=1, entries=entries), ensure_ascii=False, indent=2) + '\n'
    if len(result.encode()) > MAX_BYTES:
        raise ValueError('The browse index exceeds 4 MiB.')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    text = build(root)
    if not args.check:
        (root / 'index.json').write_text(text, encoding='utf-8')
    print(f'Validated {len(json.loads(text)["entries"])} free configs.')
