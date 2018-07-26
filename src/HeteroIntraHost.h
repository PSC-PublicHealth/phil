#ifndef _PHIL_HeteroIntraHost_H
#define _PHIL_HeteroIntraHost_H

#include <vector>
#include <map>

#include "IntraHost.h"
#include "Infection.h"
#include "Trajectory.h"
#include "Transmission.h"

class Infection;
class Trajectory;
class Age_Map;

class HeteroIntraHost : public IntraHost {
    // TODO Move reqd stuff from disease to here
  public:
    HeteroIntraHost();
    ~HeteroIntraHost();

    /**
     * Get the infection Trajectory
     *
     * @param infection
     * @param loads
     * @return a pointer to a Trajectory object
     */
    Trajectory * get_trajectory(Infection * infection, Transmission::Loads * loads);

    /**
     * Set the attributes for the IntraHost
     *
     * @param dis the disease to which this IntraHost model is associated
     */
    void setup(Disease *disease);
    int get_days_latent();
    int get_days_asymp();
    int get_days_symp();
    int get_days_susceptible();
    int get_symptoms();

    double get_asymp_infectivity() {return asymp_infectivity;}
    double get_symp_infectivity() {return symp_infectivity;}
    int get_max_days() {return max_days;}
    double get_prob_symptomatic() {return prob_symptomatic;}
    int get_infection_model() {return infection_model;}

  private:

    double asymp_infectivity;
    double symp_infectivity;
    int infection_model;
    int max_days_latent;
    int max_days_asymp;
    int max_days_symp;
    int max_days;
    double *days_latent;
    double *days_asymp;
    double *days_symp;
    double prob_symptomatic;
    void read_hetero_infectivity_params(int disease_id);
    Age_Map ** hetero_infectivity_location_map;
    Age_Map ** hetero_infectivity_scale_map;
    int hetero_infectivity_distribution;

};

#endif
