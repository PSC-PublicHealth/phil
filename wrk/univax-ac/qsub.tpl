#!/opt/bin/swsh -i python

#swsh -m anaconda/4.3.0
#swsh -e phil 

#PBS -l walltime={{ walltime or '00:30:00' }}
#PBS -l mem={{ mem or '4gb' }}
#PBS -l nodes=1:ppn={{ ppn or '8' }}
#PBS -N {{ jobname }}
#PBS -d {{ tempdir }}
#PBS -o {{ stdout }}
#PBS -e {{ stderr }}

class log(object):
    @staticmethod
    def info(s):
        print(s)
    @staticmethod
    def warn(s):
        print(s)
    @staticmethod
    def error(s):
        print(s)

try:
    stat = ''

    import sh
    import os
    import sys
    import time
    from shlex import split as shlex_split
    from random import randint

    jobname = os.environ['PBS_JOBNAME']
    log.info(jobname)    
    
    jobid = os.environ['PBS_JOBID']
    log.info(jobid)
  
    phil_home = os.environ['PHIL_HOME'] 
    log.info(phil_home)
    phil = sh.Command(os.path.join(phil_home, 'bin', 'phil'))
    poe = sh.Command(sh.which('poe.py'))

    try:
        phil('{{ paramfile }}')
        poe(p='{{ synthetic_population }}', r='{{ event_report_file }}', 
                o='{{ poe_output_file }}', c='none', g='config.yaml', f='{{ poe_format }}')
    except sh.SignalException_SIGABRT as e:
        print(e.stdout)
        stat += str(e.stdout)
        stat += '\n'
        stat += str(e.stderr)
        raise
except Exception as e:
    stat += '\n%s.%s failed!' % (jobname, jobid)
    raise
finally:
    with open('{{ statusfile }}', 'w') as f:
        f.write(stat)
    os.remove('{{ lockfile }}')
    print(sh.checkjob('-vvv', jobid))

