#include <vector>
#include <map>

#include "Age_Map.h"
#include "HeteroIntraHost.h"
#include "Disease.h"
#include "Infection.h"
#include "Trajectory.h"
#include "Params.h"
#include "Random.h"

HeteroIntraHost::HeteroIntraHost() {
    prob_symptomatic = -1.0;
    asymp_infectivity = -1.0;
    symp_infectivity = -1.0;
    max_days_latent = -1;
    max_days_asymp = -1;
    max_days_symp = -1;
    max_days = 0;
    days_latent = NULL;
    days_asymp = NULL;
    days_symp = NULL;
}

HeteroIntraHost::~HeteroIntraHost() {
    delete [] days_latent;
    delete [] days_asymp;
    delete [] days_symp;
}

void HeteroIntraHost::setup(Disease *disease) {
    IntraHost::setup(disease);

    int id = disease->get_id();
    Params::get_indexed_param("symp",id,&prob_symptomatic);
    Params::get_indexed_param("symp_infectivity",id,&symp_infectivity);
    Params::get_indexed_param("asymp_infectivity",id,&asymp_infectivity);

    int n;
    Params::get_indexed_param("days_latent",id,&n);
    days_latent = new double [n];
    max_days_latent = Params::get_indexed_param_vector("days_latent", id, days_latent) -1;

    Params::get_indexed_param("days_asymp",id,&n);
    days_asymp = new double [n];
    max_days_asymp = Params::get_indexed_param_vector("days_asymp", id, days_asymp) -1;

    Params::get_indexed_param("days_symp",id,&n);
    days_symp = new double [n];
    max_days_symp = Params::get_indexed_param_vector("days_symp", id, days_symp) -1;

    Params::get_indexed_param("infection_model", id, &infection_model);

    if (max_days_asymp > max_days_symp) {
        max_days = max_days_latent + max_days_asymp;
    } else {
        max_days = max_days_latent + max_days_symp;
    }

    read_hetero_infectivity_params(1);
}

Trajectory * HeteroIntraHost::get_trajectory(Infection *infection, Transmission::Loads * loads) {
    // TODO  take loads into account - multiple strains
    Trajectory * trajectory = new Trajectory();
    int sequential = get_infection_model();

    int will_be_symptomatic = get_symptoms();

    int days_latent = get_days_latent();
    int days_incubating;
    int days_asymptomatic = 0;
    int days_symptomatic = 0;
    double symptomatic_infectivity = get_symp_infectivity();
    double asymptomatic_infectivity = get_asymp_infectivity();
    double symptomaticity = 1.0;

    if (sequential) { // SEiIR model
        days_asymptomatic = get_days_asymp();

        if (will_be_symptomatic) {
            days_symptomatic = get_days_symp();
        }
    } else { // SEIR/SEiR model
        if (will_be_symptomatic) {
            days_symptomatic = get_days_symp();
        } else {
            days_asymptomatic = get_days_asymp();
        }
    }

    days_incubating = days_latent + days_asymptomatic;

    map<int, double> :: iterator it;

    for (it = loads->begin(); it != loads->end(); it++) {
        vector<double> infectivity_trajectory(days_latent, 0.0);
        infectivity_trajectory.insert(infectivity_trajectory.end(), days_asymptomatic, asymptomatic_infectivity);
        infectivity_trajectory.insert(infectivity_trajectory.end(), days_symptomatic, symptomatic_infectivity);
        trajectory->set_infectivity_trajectory(it->first, infectivity_trajectory);
    }

    vector<double> symptomaticity_trajectory(days_incubating, 0.0);
    symptomaticity_trajectory.insert(symptomaticity_trajectory.end(), days_symptomatic, symptomaticity);
    trajectory->set_symptomaticity_trajectory(symptomaticity_trajectory);

    return trajectory;
}

int HeteroIntraHost::get_days_latent() {
    int days = 0;
    days = draw_from_distribution(max_days_latent, days_latent);
    return days;
}

int HeteroIntraHost::get_days_asymp() {
    int days = 0;
    days = draw_from_distribution(max_days_asymp, days_asymp);
    return days;
}

int HeteroIntraHost::get_days_symp() {
    int days = 0;
    days = draw_from_distribution(max_days_symp, days_symp);
    return days;
}

int HeteroIntraHost::get_days_susceptible() {
    return 0;
}

int HeteroIntraHost::get_symptoms() {
    return (RANDOM() < prob_symptomatic);
}

void HeteroIntraHost::read_hetero_infectivity_params(int num_diseases) {

//    char s[80];
//
//    sprintf(s, "infectivity_profile_probabilities[%d]", disease_id);
//    Params::get_param(s, &numProfiles);
//    Params::get_param_vector(s, probabilities);
//
//    vector<double> infProfile;
//    sprintf(s, "fixed_infectivity_profile[%d][%d]", disease_id, i);
//    Params::get_param_vector(s, infProfile);
//    infLibrary.push_back(infProfile);
//
//    vector<double> sympProfile;
//    sprintf(s, "fixed_symptomaticity_profile[%d][%d]", disease_id, i);
//    Params::get_param_vector(s, sympProfile);
//    sympLibrary.push_back(sympProfile);
    

    Params::get_param("hetero_infectivity_distribution", &hetero_infectivity_distribution);

    hetero_infectivity_location_map = new Age_Map*[num_diseases];
    hetero_infectivity_scale_map = new Age_Map*[num_diseases];

    for (int d=0; d<num_diseases; d++) {
        hetero_infectivity_location_map[d] = new Age_Map("HeteroInfectivityLocation");
        hetero_infectivity_location_map[d]->read_from_input("hetero_infectivity_location_map", d); 

        hetero_infectivity_scale_map[d] = new Age_Map("HeteroInfectivityScale");
        hetero_infectivity_scale_map[d]->read_from_input("hetero_infectivity_scale_map", d); 
    }
    
}










