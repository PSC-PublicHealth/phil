#!/bin/bash

code_dir=$1
input_dir=$2
trans=$3
efficacy=$4

export PHIL_HOME=${code_dir}
export OMP_NUM_THREADS=1

results_dir=${input_dir}/trans-${trans}_efficacy-${efficacy}
mkdir ${results_dir}

cp ${input_dir}/params.vaccinomics ${results_dir}/params.vaccinomics
cp ${input_dir}/primary_cases_vaccinomics.txt ${results_dir}/primary_cases_vaccinomics.txt

cd ${results_dir}

for i in {1..30};
do
  day_of_week=$(shuf -i 0-6 -n 1)
  seed=$RANDOM
  realization_number=${i}

  # Set the start date
  if [ ${day_of_week} -eq 0 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-01/' params.vaccinomics
  elif [ ${day_of_week} -eq 1 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-02/' params.vaccinomics
  elif [ ${day_of_week} -eq 2 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-03/' params.vaccinomics
  elif [ ${day_of_week} -eq 3 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-04/' params.vaccinomics
  elif [ ${day_of_week} -eq 4 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-05/' params.vaccinomics
  elif [ ${day_of_week} -eq 5 ]
  then
    sed -i 's/start_date = .*/start_date = 2012-01-06/' params.vaccinomics
  else
    sed -i 's/start_date = .*/start_date = 2012-01-07/' params.vaccinomics
  fi

  # Set the random seed
  sed -i "s/seed = .*/seed = ${seed}/" params.vaccinomics

  # Set the trans parameter
  sed -i "s/trans\[0\] = .*/trans[0] = ${trans}/" params.vaccinomics

  # Set the efficacy parameter
  sed -i "s/vaccine_dose_efficacy_values\[0\]\[0\] = .*/vaccine_dose_efficacy_values[0][0] = 1 ${efficacy}/" params.vaccinomics

  # Run PHIL
  ${PHIL_HOME}/bin/phil params.vaccinomics

  # Create the output directory and move the results there
  mkdir ${results_dir}/${realization_number}
  mv ${results_dir}/OUT ${results_dir}/${realization_number}/

done
