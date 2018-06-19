//
//
// File: Vaccine_Priority_Policies.cpp
//

#include "Vaccine_Priority_Decisions.h"
#include "Vaccine_Priority_Policies.h"
#include "Manager.h"
#include "Vaccine_Manager.h"
#include "Vaccines.h"
#include "Random.h"
#include "Person.h"
#include "Health.h"
#include "Demographics.h"
#include "Age_Map.h"
#include <iostream>

Vaccine_Priority_Decision_Specific_Age::Vaccine_Priority_Decision_Specific_Age() : Decision() { }

Vaccine_Priority_Decision_Specific_Age::Vaccine_Priority_Decision_Specific_Age(Policy *p): Decision(p) {
    name = "Vaccine Priority Decision Specific Age";
    type = "Y/N";
    policy = p;
}

int Vaccine_Priority_Decision_Specific_Age::evaluate(Person* person, int disease, int day) {
    Vaccine_Manager* vcm = dynamic_cast < Vaccine_Manager* >(policy->get_manager());
    int low_age = vcm->get_vaccine_priority_age_low();
    int high_age = vcm->get_vaccine_priority_age_high();

    if (person->get_age() >= low_age && person->get_age() <= high_age) {
        return 1;
    }
    return -1;
}

Vaccine_Priority_Decision_Pregnant::Vaccine_Priority_Decision_Pregnant() : Decision() { }

Vaccine_Priority_Decision_Pregnant::Vaccine_Priority_Decision_Pregnant(Policy *p): Decision(p) {
    name = "Vaccine Priority Decision to Include Pregnant Women";
    type = "Y/N";
    policy = p;
}

int Vaccine_Priority_Decision_Pregnant::evaluate(Person* person, int disease, int day) {
    if (person->get_demographics()->is_pregnant()) return 1;
    return -1;
}

Vaccine_Priority_Decision_At_Risk::Vaccine_Priority_Decision_At_Risk() : Decision() { }

Vaccine_Priority_Decision_At_Risk::Vaccine_Priority_Decision_At_Risk(Policy *p): Decision(p) {
    name = "Vaccine Priority Decision to Include At_Risk";
    type = "Y/N";
    policy = p;
}

int Vaccine_Priority_Decision_At_Risk::evaluate(Person* person, int disease, int day) {
    if (person->get_health()->is_at_risk(disease)) return 1;
    return -1;
}


Vaccine_Priority_Decision_No_Priority::Vaccine_Priority_Decision_No_Priority() : Decision() { }

Vaccine_Priority_Decision_No_Priority::Vaccine_Priority_Decision_No_Priority(Policy *p) : Decision(p) {
    name = "Vaccine Priority Decision No Priority";
    type = "Y/N";
    policy=p;
}

int Vaccine_Priority_Decision_No_Priority::evaluate(Person* person, int disease, int day) {
    return -1;
}

// Decisions that control coverage for overall vaccination

Vaccine_Priority_Decision_AgeMap_Coverage::Vaccine_Priority_Decision_AgeMap_Coverage(): Decision() { }

Vaccine_Priority_Decision_AgeMap_Coverage::Vaccine_Priority_Decision_AgeMap_Coverage(Policy *p) : Decision(p) {
    name = "Vaccine Priority Decision for Age Specific Coverage";
    type = "Y/N";
    policy = p;
}

int Vaccine_Priority_Decision_AgeMap_Coverage::evaluate(Person* person, int disease, int day) {
    Vaccine_Manager* vcm = dynamic_cast < Vaccine_Manager* >(policy->get_manager());
    // modify to account for age-specific coverage 
    int num_vaccines = vcm->get_vaccines()->get_num_vaccines();
    int vaccine_id = (int) (RANDOM() * (num_vaccines - 1));
    double coverage = vcm->get_vaccine_coverage_age_map(vaccine_id)->find_value(person->get_age());
    if (RANDOM() < coverage) return 1;
    else return -1;
}

// Decisions that control age-specific coverage for multiple vaccines

Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage::Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage(): Decision() { }

Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage::Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage(Policy *p) : Decision(p) {
    name = "Vaccine Priority Decision for Age Specific Coverage of Multiple Vaccines and Dynamic Demographics (Births and Deaths)";
    type = "Y/N";
    policy = p;

    noise = true;

    Vaccine_Manager* vcm = dynamic_cast < Vaccine_Manager* >(policy->get_manager());
    int num_vaccines = vcm->get_vaccines()->get_num_vaccines();
    for (int i=0; i<num_vaccines; ++i) {
        vaccine_counts_by_bin.push_back(std::map<int,double>());
        vaccine_total_counts.push_back(0.0);
    }
}

int Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage::evaluate(Person* person, int disease, int day) {
    // always accept everybody into the queue; vaccine and age specific coverage proportions will be tracked
    // and subsequent calls to evaluate that supply the vaccine id will decide whether or not to administer the
    // vaccine or to defer (ie, do nothing, but do not remove the agent from the queu)
    return 1; 
}

int Vaccine_Priority_Decision_MultiVaccine_AgeMap_Coverage::reevaluate(Person* person, int disease, int day, int vaccine_id, bool commit) {
    Vaccine_Manager* vcm = dynamic_cast < Vaccine_Manager* >(policy->get_manager());
    int age = person->get_age();
    int bin = vcm->get_vaccine_coverage_age_map(vaccine_id)->find_bin(age);
    double target_coverage = vcm->get_vaccine_coverage_age_map(vaccine_id)->find_value(age);
    std::map<int,double> & bin_counts = vaccine_counts_by_bin[vaccine_id];
    double current_coverage;
    double resulting_coverage_1;
    double resulting_coverage_2;

    if (bin_counts.find(bin) == bin_counts.end()) {
        bin_counts[bin] = 0.0;        
    }

    int return_val = 0;
    if (target_coverage <= 0.0) {
        return_val = 0;
    }
    else {
        if (bin_counts[bin] == 0.0) {
            if (commit) {
                bin_counts[bin] += 1.0;
                vaccine_total_counts[vaccine_id] += 1.0;
            }
            return_val = 1;
        }
        else {
            current_coverage = (bin_counts[bin]) / (vaccine_total_counts[vaccine_id]);
            resulting_coverage_1 = (bin_counts[bin] + 1.0) / (vaccine_total_counts[vaccine_id] + 1.0);
            resulting_coverage_2 = (bin_counts[bin]) / (vaccine_total_counts[vaccine_id] + 1.0);

            bool accept = (current_coverage < target_coverage
                                || resulting_coverage_1 < target_coverage 
                                || resulting_coverage_2 < target_coverage); 
            if (!accept) {
                if (!commit) {
                    noise = RANDOM() < 0.00001;
                }
                accept = accept || noise;
            }

            if (accept) {
                if (commit) {
                    bin_counts[bin] += 1.0;
                    vaccine_total_counts[vaccine_id] += 1.0;
                }
                return_val = 1;
            }
            else {
                return_val = 0;
            }
        }
    }
//    std::cout << "VACCINE " << vaccine_id << " Target " << target_coverage << " Current " << current_coverage << "Age " << age << " Bin " << bin << std::endl;
//    std::map<int,double>::iterator itr;
//    std::cout << "VACCINE " << vaccine_id << " COVERAGE:";
//    for (itr=bin_counts.begin(); itr!=bin_counts.end(); ++itr) {
//        std::cout << "  " << itr->second; 
//    }
//    std::cout << std::endl;

    return return_val;
}

















