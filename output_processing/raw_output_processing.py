from argparse import ArgumentParser
import ast
from multiprocessing import Process, Queue
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple


def main(results_dir: str, people_file: str, number_of_processes: int) -> None:
    """
    Use multiple processors to process a batch of realizations of PHIL to compute the 4 outputs Sarah wants.
    These batch of realizations should all be contained in the same directory. That directory should have nothing but
    one directory per realization. Example being:
      results_dir/
        |- 1/
        |  |- OUT/
        |      |- report1.json_lines
        |- 2/
        |  |- OUT/
        |      |- report1.json_lines
        |- 3/
        ...
    """
    people_df = pd.read_csv(people_file, index_col=0)
    people_to_age_mapping = people_df.age.to_dict()

    ages_vaccinated_queue = Queue()
    infections_by_age_queue = Queue()
    new_infections_by_day_queue = Queue()
    total_infected_by_day_queue = Queue()

    jobs = []
    realization_assignments = assign_realizations_to_processes(results_dir, number_of_processes)
    for realizations in realization_assignments:
        process = Process(
            target=process_realizations,
            args=(
                realizations,
                people_to_age_mapping,
                ages_vaccinated_queue,
                infections_by_age_queue,
                new_infections_by_day_queue,
                total_infected_by_day_queue,
            )
        )
        jobs.append(process)
        process.start()

    # This is a little fragile as it assumes you only have your realizations in the results directory
    number_of_realizations = len([directory for directory in Path(results_dir).iterdir() if directory.is_dir()])

    ages_vaccinated = []
    infections_by_age = []
    new_infections_by_day = []
    total_infected_by_day = []
    for _ in range(number_of_realizations):
        ages_vaccinated.append(ages_vaccinated_queue.get())
        infections_by_age.append(infections_by_age_queue.get())
        new_infections_by_day.append(new_infections_by_day_queue.get())
        total_infected_by_day.append(total_infected_by_day_queue.get())

    for process in jobs:
        process.join()

    pd.DataFrame(ages_vaccinated).T.to_csv('{}/ages_vaccinated.csv'.format(results_dir), index_label='age')
    pd.DataFrame(infections_by_age).T.to_csv('{}/infections_by_age.csv'.format(results_dir), index_label='age')
    pd.DataFrame(new_infections_by_day).T.to_csv('{}/new_infections_by_day.csv'.format(results_dir), index_label='day')
    pd.DataFrame(total_infected_by_day).T.to_csv('{}/total_infected_by_day.csv'.format(results_dir), index_label='day')


def assign_realizations_to_processes(results_dir: str, number_of_processes: int) -> Generator[List[Path], None, None]:
    results_dir = Path(results_dir)
    # This is a little fragile as it assumes you only have your realizations in the results directory
    realizations = [directory for directory in results_dir.iterdir() if directory.is_dir()]
    for i in range(number_of_processes):
        yield realizations[i::number_of_processes]


def process_realizations(realizations: List[Path], people_to_age_mapping: Dict[int, int], ages_vaccinated_queue: Queue,
                         infections_by_age_queue: Queue, new_infections_by_day_queue: Queue,
                         total_infected_by_day_queue: Queue) -> None:
    """
    Method given to each process to process each realization and put the results into the queue for the main process to
    combine and write to a file.
    """
    for realization in realizations:
        processor = RealizationProcessor(realization, people_to_age_mapping)
        ages_vaccinated, infections_by_age, new_infections_by_day, total_infected_by_day = processor.process()

        ages_vaccinated_queue.put(ages_vaccinated)
        infections_by_age_queue.put(infections_by_age)
        new_infections_by_day_queue.put(new_infections_by_day)
        total_infected_by_day_queue.put(total_infected_by_day)


class RealizationProcessor:
    """
    Class used to process each individual realization's output file. It will not write out any files, it will simply
    return the `Dict`s containing the output data.
    """
    def __init__(self, directory: Path, people_to_age_mapping: Dict[int, int]) -> None:
        self.output_file = directory / "OUT" / "report1.json_lines"
        self.people_to_age_mapping = people_to_age_mapping
        # Ranges are hardcoded for simplicity
        self.ages_vaccinated = {age: 0 for age in range(110)}
        self.infections_by_age = {age: 0 for age in range(110)}
        self.new_infections_by_day = {day: 0 for day in range(200)}
        self.total_infected_by_day = {day: 0 for day in range(200)}

    def process(self) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int]]:
        with self.output_file.open() as report:
            # Discard the header
            report.readline()

            while True:
                line = report.readline()
                try:
                    line = ast.literal_eval(line)
                    if line['event'] == 'vaccination':
                        self.process_vaccination(line)
                    elif line['event'] == 'infection':
                        self.process_infection(line)
                    else:
                        # Not the best way to handle unexpected events in a multiprocess environment,
                        # but I don't think any other types of events currently exist in PHIL.
                        raise RuntimeError("Received an unexpected event type: {}", line)
                except SyntaxError:
                    # An empty line will raise a SyntaxError when you try to evaluate it, so
                    # this is a simple way to tell when we've reached the end of the file.
                    break

        return self.ages_vaccinated, self.infections_by_age, self.new_infections_by_day, self.total_infected_by_day

    def process_vaccination(self, event: Dict[str, Any]) -> None:
        person_vaccinated = event['person']
        age_vaccinated = self.people_to_age_mapping[person_vaccinated]
        self.ages_vaccinated[age_vaccinated] += 1

    def process_infection(self, event: Dict[str, Any]) -> None:
        # infections_by_age
        person_infected = event['person']
        age_infected = self.people_to_age_mapping[person_infected]
        self.infections_by_age[age_infected] += 1

        day_infected = event['infectious']

        # new_infections_by_day
        self.new_infections_by_day[day_infected] += 1

        # total_infected_by_day
        for day in range(day_infected, event['recovered']):
            self.total_infected_by_day[day] += 1


if __name__ == '__main__':
    parser = ArgumentParser(description="Processes PHIL output into the various counts that Sarah wants.")
    parser.add_argument('results_dir', type=str, help='The path to directory containing all the output files')
    parser.add_argument('people_file', type=str, help='The path to the synthetic population people file')
    parser.add_argument('number_of_processors', type=int, help='The number of processors you want to use')
    args = parser.parse_args()
    main(
        args.results_dir,
        args.people_file,
        args.number_of_processors,
    )
