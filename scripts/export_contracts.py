import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'apps/api'))
from controlcheck.main import create_app

target = root / 'packages/contracts/openapi.json'
target.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'Exported {target.name}')
