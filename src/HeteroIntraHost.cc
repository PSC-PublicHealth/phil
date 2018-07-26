#include <vector>
#include <map>

#include "HeteroIntraHost.h"
#include "Disease.h"
#include "Infection.h"
#include "Trajectory.h"
#include "Params.h"
#include "Random.h"

HeteroIntraHost::HeteroIntraHost() {
    prob_symptomatic = -1.0;
    hetero_infectivity_asymp_multiplier = -1.0; 
    hetero_infectivity_location_map = NULL;
    hetero_infectivity_scale_map = NULL;
    hetero_infectivity_distribution = -1;
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
    Params::get_indexed_param("symp", id, &prob_symptomatic);
    Params::get_indexed_param("hetero_infectivity_asymp_multiplier", id, &hetero_infectivity_asymp_multiplier);

    int n;
    Params::get_indexed_param("days_latent", id, &n);
    days_latent = new double [n];
    max_days_latent = Params::get_indexed_param_vector("days_latent", id, days_latent) -1;

    Params::get_indexed_param("days_asymp", id, &n);
    days_asymp = new double [n];
    max_days_asymp = Params::get_indexed_param_vector("days_asymp", id, days_asymp) -1;

    Params::get_indexed_param("days_symp", id, &n);
    days_symp = new double [n];
    max_days_symp = Params::get_indexed_param_vector("days_symp", id, days_symp) -1;

    Params::get_indexed_param("infection_model", id, &infection_model);

    if (max_days_asymp > max_days_symp) {
        max_days = max_days_latent + max_days_asymp;
    } else {
        max_days = max_days_latent + max_days_symp;
    }

    Params::get_indexed_param("hetero_infectivity_distribution", id, &hetero_infectivity_distribution);
    Params::get_indexed_param("hetero_infectivity_asymp_multiplier", id, &hetero_infectivity_asymp_multiplier);
    hetero_infectivity_location_map = new Age_Map("HeteroInfectivityLocation");
    hetero_infectivity_location_map->read_from_input("hetero_infectivity_location_map", id); 
    hetero_infectivity_scale_map = new Age_Map("HeteroInfectivityScale");
    hetero_infectivity_scale_map->read_from_input("hetero_infectivity_scale_map", id); 
 }

double HeteroIntraHost::check_hetero_infectivity() {
    double loc;
    double scale;
    if (hetero_infectivity_distribution != 0) {
        Utils::phil_abort("Unsupported Heterogeneous Infectivity Distribution Value!");
    }
    else if (hetero_infectivity_distribution == 0 ) {// Uniform Distribution
        for (int i=0; i<110; i++) {
            loc = hetero_infectivity_location_map->find_value(i);
            scale = hetero_infectivity_scale_map->find_value(i);
            if ((loc - (scale/2.0)) < 0) {
                Utils::phil_abort("location and scale resulted in negative infectivity");
            }
        }
    }
}

double HeteroIntraHost::get_asymp_infectivity(int age) {
    double inf = hetero_infectivity_asymp_multiplier * get_symp_infectivity(age);
    //cout << "asymptomatic infectivity: " << inf << endl;
    return inf;
}

double HeteroIntraHost::get_symp_infectivity(int age) {
    double loc = hetero_infectivity_location_map->find_value(age);
    double scale = hetero_infectivity_scale_map->find_value(age);
    double inf;
    if (hetero_infectivity_distribution == 0 ) {// Uniform Distribution
        inf = (loc - (scale/2.0)) + (scale * RANDOM());
    }
    else {
        Utils::phil_abort("no valid hetero infectivity model specified");
    }
    //cout << " loc " << loc << " scale " << scale << " age " << age << endl;
    //cout << " symptomatic infectivity: " << inf << endl;
    return inf;
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

    int infectee_age = infection->get_age_at_exposure();
    
    double symptomatic_infectivity = get_symp_infectivity(infectee_age);
    double asymptomatic_infectivity = get_asymp_infectivity(infectee_age);
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












