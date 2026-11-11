"""Replay real saved eval evidence without calling an API or changing results."""
import argparse
import json
from pathlib import Path
import sys


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', default='H1')
    parser.add_argument('--file', default='eval_after.json')
    args = parser.parse_args()
    path = Path(args.file)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    report = json.loads(path.read_text(encoding='utf-8'))
    case = next((c for c in report['cases'] if c['id'] == args.case.upper()), None)
    if case is None:
        parser.error('Case not found in report')
    print(f"File: {path.name}; case: {case['id']}; score: {case['grade'].get('score')}")
    print('Question:', case['question'])
    for event in case['result']['trace']:
        kind = event.get('event')
        print(f"  step {event.get('step')}: {kind}", end='')
        if kind == 'model':
            print(f" finish={event.get('finish')}")
        elif kind == 'tool':
            print(f" {event['name']} {json.dumps(event['arguments'], ensure_ascii=False)}")
            result = event.get('result', {})
            if result.get('url'):
                print('    URL:', result['url'])
            if 'updates' in result:
                print(f"    updates: {len(result['updates'])}/{result.get('updates_total')}; "
                      f"truncated: {any(u.get('truncated') for u in result['updates'])}")
        else:
            print(' ', json.dumps(event, ensure_ascii=False))
    print('\nAnswer:\n' + case['result']['answer'])
    print('\nJudge reason:', case['grade'].get('reason'))
    print('Judge improvement:', case['grade'].get('improvement'))


if __name__ == '__main__':
    main()
