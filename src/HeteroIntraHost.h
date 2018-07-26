#ifndef _PHIL_HeteroIntraHost_H
#define _PHIL_HeteroIntraHost_H

#include <vector>
#include <map>

#include "Age_Map.h"
#include "IntraHost.h"
#include "Infection.h"
#include "Trajectory.h"
#include "Transmission.h"

class Infection;
class Trajectory;

class HeteroIntraHost : public IntraHost {
    // TODO Move reqd stuff from disease to here
  public:
    HeteroIntraHost();
    ~HeteroIntraHost();

    Trajectory * get_trajectory(Infection * infection, Transmission::Loads * loads);
    int hetero_infectivity_distribution;

    void setup(Disease *disease);
    int get_days_latent();
    int get_days_asymp();
    int get_days_symp();
    int get_days_susceptible();
    int get_symptoms();

    double get_asymp_infectivity(int age);
    double get_symp_infectivity(int age);

    int get_max_days() {return max_days;}
    double get_prob_symptomatic() {return prob_symptomatic;}
    int get_infection_model() {return infection_model;}

  private:
    double check_hetero_infectivity();
    double hetero_infectivity_asymp_multiplier;
    int infection_model;
    int max_days_latent;
    int max_days_asymp;
    int max_days_symp;
    int max_days;
    double *days_latent;
    double *days_asymp;
    double *days_symp;
    double prob_symptomatic;
    Age_Map * hetero_infectivity_location_map;
    Age_Map * hetero_infectivity_scale_map;

};

#endif
