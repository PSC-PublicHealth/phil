#!/bin/bash

export PHIL_HOME=[SET THIS]
export OMP_NUM_THREADS=1

for i in seq `1 30`
do
    bash ./runner.sh $(shuf -i 0-6 -n 1) $RANDOM ${i} trans0.68
done
