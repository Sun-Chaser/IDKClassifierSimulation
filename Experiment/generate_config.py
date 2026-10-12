"""Generate a runner config with consecutive seeds starting at 42."""
import argparse
import json
from pathlib import Path

if __package__:
    from .run_experiments import validate
else:
    from run_experiments import validate


def expand_range(values, name):
    """Expand START END [STEP], including END when reached by STEP."""
    if len(values) not in (2, 3):
        raise ValueError(f'{name} requires START END [STEP]')
    numbers = [int(value) for value in values]
    if len(numbers) == 3 and numbers[2] == 0:
        raise ValueError(f'{name}: STEP must not be zero')
    start, end = numbers[:2]
    step = numbers[2] if len(numbers) == 3 else 1
    result = list(range(start, end + (1 if step > 0 else -1), step))
    if not result:
        raise ValueError(f'{name}: range must not be empty (check STEP direction)')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m', nargs='+', type=int, default=[3, 4],
                        metavar='INT', help='START END [STEP], inclusive END')
    parser.add_argument('--n', nargs='+', type=int, default=[5, 10, 5],
                        metavar='INT', help='START END [STEP], inclusive END')
    parser.add_argument('--k', nargs='+', default=['1', '2'],
                        metavar='VALUE', help='START END [STEP], or all')
    parser.add_argument('--include-all', action='store_true',
                        help='Append unrestricted search to the k range')
    parser.add_argument('--trials', type=int, default=3,
                        help='Number of seeds: 42, 43, ... (default: 3)')
    parser.add_argument('--row-sizes', choices=['equal', 'random'], default='equal')
    parser.add_argument('--timeout-seconds', type=float, default=60)
    parser.add_argument('--max-states', type=int, default=1000000)
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().parent / 'Config' / 'config.json',
                        help='Config to write (replaces an existing file)')
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    try:
        config = {
            'm': expand_range(args.m, '--m'),
            'n': expand_range(args.n, '--n'),
            'k': ['all'] if args.k == ['all'] else expand_range(args.k, '--k'),
            'seeds': list(range(42, 42 + args.trials)),
            'row_sizes': args.row_sizes,
            'timeout_seconds': args.timeout_seconds,
            'max_states': args.max_states,
        }
        if args.include_all and 'all' not in config['k']:
            config['k'].append('all')
        validate(config)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2, allow_nan=False) + '\n')
    print(f'Config written to {args.output.resolve()}')


if __name__ == '__main__':
    main()
