#!/bin/bash

mkdir /pylon5/olympus/hertenst/vaccinomics/$3

cp params.vaccinomics /pylon5/olympus/hertenst/vaccinomics/$3/
cp primary_cases_vaccinomics.txt /pylon5/olympus/hertenst/vaccinomics/$3/

cd /pylon5/olympus/hertenst/vaccinomics/$3

if [ $1 -eq 0 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-01/' params.vaccinomics
elif [ $1 -eq 1 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-02/' params.vaccinomics
elif [ $1 -eq 2 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-03/' params.vaccinomics
elif [ $1 -eq 3 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-04/' params.vaccinomics
elif [ $1 -eq 4 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-05/' params.vaccinomics
elif [ $1 -eq 5 ]
then
  sed -i 's/start_date = .*/start_date = 2012-01-06/' params.vaccinomics
else
  sed -i 's/start_date = .*/start_date = 2012-01-07/' params.vaccinomics
fi

sed -i "s/seed = .*/seed = $2/" params.vaccinomics

phil params.vaccinomics
