from argparse import ArgumentParser
import pandas as pd
from pathlib import Path


def main(results_dir: str) -> None:
    """Computes the summary statistics Sarah wants on the 4 processed output files."""
    filenames = [
        'age_groups_vaccinated',
        'infections_by_age_group',
        'new_infections_by_day',
        'total_infected_by_day',
    ]

    for filename in filenames:
        in_path = Path(results_dir) / '{}.csv'.format(filename)
        raw_data = pd.read_csv(in_path, index_col=0)

        summary_stats = pd.concat([
            raw_data.mean(axis=1),
            raw_data.median(axis=1),
            raw_data.std(axis=1),
            raw_data.quantile(0.025, axis=1),
            raw_data.quantile(0.975, axis=1),
            raw_data.quantile(0.25, axis=1),
            raw_data.quantile(0.75, axis=1),
            raw_data.min(axis=1),
            raw_data.max(axis=1),
        ], axis=1)
        summary_stats.columns = [
            'mean',
            'median',
            'std',
            '2.5%',
            '97.5%',
            '25%',
            '75%',
            'min',
            'max',
        ]

        out_path = Path(results_dir) / '{}_summary_stats.csv'.format(filename)
        summary_stats.to_csv(out_path)


if __name__ == '__main__':
    parser = ArgumentParser(description="Computes the summary statistics Sarah wants on the 4 processed output files.")
    parser.add_argument('results_dir', type=str, help='The path to directory containing all the processed output files')
    args = parser.parse_args()
    main(args.results_dir)
