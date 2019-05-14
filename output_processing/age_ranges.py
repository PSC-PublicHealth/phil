from argparse import ArgumentParser
import pandas as pd
from pathlib import Path


def main(results_dir: str) -> None:
    """Group the age related outputs using the age groupings Sarah wants."""
    # Hard coding the age groupings for simplicity
    age_cutoffs = [0, 5, 18, 45, 65, 120]
    range_labels = ["0-4", "5-17", "18-44", "45-64", "65+"]

    in_file_out_file_pairings = [
        ('infections_by_age.csv', 'infections_by_age_group.csv'),
        ('ages_vaccinated.csv', 'age_groups_vaccinated.csv'),
    ]

    for in_file, out_file in in_file_out_file_pairings:
        in_path = Path(results_dir) / in_file
        ungrouped_data = pd.read_csv(in_path, index_col=0)

        age_range_categorizations = pd.cut(ungrouped_data.index, bins=age_cutoffs, labels=range_labels, right=False)
        grouped_data = ungrouped_data.groupby(age_range_categorizations).sum()

        out_path = Path(results_dir) / out_file
        grouped_data.to_csv(out_path)


if __name__ == '__main__':
    parser = ArgumentParser(description="Group the age related outputs using the age groupings Sarah wants.")
    parser.add_argument('results_dir', type=str, help='The path to directory containing all the processed output files')
    args = parser.parse_args()
    main(args.results_dir)
