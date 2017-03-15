# coding: utf-8

import sh
import os
import re
import time
import argparse
import jinja2

import pandas as pd

from tempfile import mkdtemp
from random import randint
from collections import OrderedDict, namedtuple
from fasteners import InterProcessLock
from datetime import datetime
from PyGMO.problem import base as PyGMO_Problem_Base


# if logging is imported as a module, duplicate loggers created on reload()
import logging
log = logging.getLogger()
# NOTE: this business is necessary so that the logger is completely
# reinitialized upon a module reload
list(map(log.removeHandler, log.handlers[:]))
list(map(log.removeFilter, log.filters[:]))
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)


class PhilOptimizeAttackRateByAge(PyGMO_Problem_Base):
    age_groups = ['[0, 5)','[5, 18)','[18, 50)',
                  '[50, 65)','[65, 106)']

    synthetic_population_directory = os.path.join(os.environ['PHIL_HOME'], 'populations')
    synthetic_population_id = '2005_2009_ver2_42003'
    synthetic_population = os.path.join(synthetic_population_directory, synthetic_population_id)

    base_params = {
                'synthetic_population_directory': synthetic_population_directory,
                'synthetic_population_id': synthetic_population_id,
            }

    optimized_param_array_defaults = [
        0.198226,  # household_contacts[0]
        42.478577, # neighborhood_contacts[0]
        14.320478, # school_contacts[0]
        1.589467,  # workplace_contacts[0]
        14.320478, # classroom_contacts[0]
        1.589467,  # office_contacts[0]
        1.5,       # weekend_contact_rate[0]

        # household_prob[0] = 4
        0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
        # workplace_prob[0] = 1
        0.0575,
        # office_prob[0] = 1
        0.0575,
        # school_prob[0] = 16
        0.0435, 0, 0, 0.0435, 0, 0.0375, 0, 0.0375, 0, 0, 0.0315, 0.0315, 0.0435, 0.0375, 0.0315, 0.0575,
        # classroom_prob[0] = 16
        0.0435, 0, 0, 0.0435, 0, 0.0375, 0, 0.0375, 0, 0, 0.0315, 0.0315, 0.0435, 0.0375, 0.0315, 0.0575,
        # neighborhood_prob[0] = 4
        0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
      
        1.0,       # trans[0]
        ]

    idx = namedtuple('ArrayIndexes', ['start', 'end', 'is_indexed', 'min', 'max'])

    optimized_param_array_indexes = OrderedDict([
        ('household_contacts',    idx( 0,  1, False,  0.00,  5.00 )),
        ('neighborhood_contacts', idx( 1,  2,  False,  0.00, 50.00 )),
        ('school_contacts',       idx( 2,  3,  False,  0.00, 20.00 )),
        ('workplace_contacts',    idx( 3,  4,  False,  0.00,  4.00 )),
        ('classroom_contacts',    idx( 4,  5,  False,  0.00, 20.00 )),
        ('office_contacts',       idx( 5,  6,  False,  0.00,  4.00 )),
        ('weekend_contact_rate',  idx( 6,  7,  False,  0.00,  2.00 )),
        ('household_prob',        idx( 7,  32, True,   0.00,  1.00 )),
        ('workplace_prob',        idx( 32, 33, True,   0.00,  1.00 )),
        ('office_prob',           idx( 33, 34, True,   0.00,  1.00 )),
        ('school_prob',           idx( 34, 50, True,   0.00,  1.00 )),
        ('classroom_prob',        idx( 50, 66, True,   0.00,  1.00 )),
        ('neighborhood_prob',     idx( 66, 91, True,   0.00,  1.00 )),
        ('trans',                 idx( 91, 92, False,  0.10,  4.00 )),
        ])

    # The annual impact of seasonal influenza in the US: Measuring disease burden and costs
    # Molinari, et al; 2007
    target = pd.DataFrame(dict(
                age = ['[0, 5)','[5, 18)','[18, 50)','[50, 65)','[65, 106)'],
                attack_rate_mean = [0.203, 0.102, 0.066, 0.066, 0.090],
                attack_rate_stddev = [0.062, 0.032, 0.017, 0.017, 0.024])
                ).set_index('age').sort_index()

    target_year = 1

    def __init__(self):
        self.wrkdir = os.getcwd()
        self.phil_home = os.environ['PHIL_HOME']
        self.qsub = sh.qsub.bake('-v','PHIL_HOME=%s' % self.phil_home)
        self.base_param_file = 'params.seasonal'
        self.qsub_template_file = 'qsub.tpl'
        with open(self.qsub_template_file, 'r') as f:
            self.qsub_template = jinja2.Template(f.read())
        nobj = len(self.target.index)
        nint = 0
        ndim = 0
        lower_bounds = []
        upper_bounds = []
        for k,v in self.optimized_param_array_indexes.items():
            if v.end > ndim:
                ndim = v.end
            lower_bounds.extend([v.min] * (v.end - v.start))
            upper_bounds.extend([v.max] * (v.end - v.start))
        super(PhilOptimizeAttackRateByAge, self).__init__(ndim, nint, nobj)
        self.set_bounds(lower_bounds, upper_bounds)

    def _objfun_impl(self, x):
        opt_params = self.build_phil_opt_params(x)
        poe_output_file = self.run_phil_pipeline(opt_params)
        return self.evaluate_phil_output(poe_output_file)

    def build_phil_opt_params(self, x):
        p = OrderedDict()
        for k, i in self.optimized_param_array_indexes.items():
            if i.is_indexed:
                p['%s[0]' % k] = '%d %s' % (
                        i.end - i.start,
                        ['%f' % x[j] for j in range(i.start, i.end)])
            else:
                p['%s[0]' % k] = '%f' % x[i.start]
        return p

    def read_phil_base_params_from_file(self):
        p = {}
        with open(self.base_param_file, 'r') as f:
            for l in f:
                l = l.strip()
                if not l.startswith('#') and len(l) > 0 and '=' in l:
                    m = re.search('^(.+?) = (.+)$', l)
                    if m is not None:
                        p[m.group(1)] = m.group(2)
        return p

    def run_phil_pipeline(self, opt_params):
        tempdir_container = mkdtemp(prefix='philo_', dir=self.wrkdir)
        tempdir = mkdtemp(dir=tempdir_container)
        basename = os.path.basename(tempdir)
        log.info(tempdir)
        event_report_file = os.path.join(tempdir, 'events.json_lines')
        poe_output_file = os.path.join(tempdir, 'poe_output')
        poe_format = 'csv'

        with open(os.path.join(tempdir,'params'), 'w') as paramfile:
            params = self.read_phil_base_params_from_file()
            params.update(self.base_params)
            params.update({
                'outdir': tempdir,
                'event_report_file' : event_report_file,
                'seed': randint(1, 2147483647)
            })
            params.update(opt_params)

            for param, value in params.items():
                paramfile.write('%s = %s\n' % (param, str(value)))
            paramfile.flush()

            lockfile = os.path.join(tempdir, 'lockfile')
            lock = InterProcessLock(lockfile)
            statusfile = os.path.join(tempdir, 'statusfile')

            sh.cp(params['primary_cases_file[0]'], tempdir)
            sh.cp(params['vaccination_capacity_file'], tempdir)
            sh.cp('config.yaml', tempdir)

            qsub_template_args = dict(
                lockfile = lockfile,
                statusfile = statusfile,
                tempdir = tempdir,
                jobname = basename,
                reservation = 'depasse.0',
                paramfile = paramfile.name,
                synthetic_population = self.synthetic_population,
                event_report_file = event_report_file,
                poe_output_file = poe_output_file,
                poe_format = poe_format
                )
           
            qsub_file = os.path.join(tempdir, 'qsub.py')
            with open(qsub_file, 'w') as f:
                f.write(self.qsub_template.render(qsub_template_args))

            jobid = self.qsub(qsub_file).strip()
            sh.ln('-s', tempdir, os.path.join(tempdir_container, jobid))

            while True:
                if lock.exists():
                    break
                else:
                    print('Waiting for job %s to start' % jobid)
                time.sleep(10)
            lock.acquire(blocking=True, delay=10, max_delay=60*60)
            with open(statusfile, 'r') as f:
                stat = f.read()
                if len(stat) > 0:
                    raise Exception(stat)

        return '%s.%s' % (poe_output_file, poe_format)

    def evaluate_phil_output(self, poe_output_file):
        d1 = pd.read_csv(poe_output_file)
        d1['year'] = pd.cut(d1.day, [x for x in range(0,2880,360)],
                include_lowest=True, right=True).cat.codes + 1

        def yearly_stats(s):
            return pd.Series({
                'N_p': s['N_p'].mean(),
                'IS_i': s['IS_i'].sum(),
                'attack_rate': s['IS_i'].sum() / s['N_p'].mean(),
            })
        d2 = d1.groupby(['year','age']).apply(yearly_stats)
        d2 = d2.xs(self.target_year, level='year')
        d3 = d2.join(self.target)
        d3['z_abs'] = ((d3.attack_rate - d3.attack_rate_mean) / d3.attack_rate_stddev).abs()
        d3 = d3.sort_index(level='age')

        return d3.z_abs.tolist()


































