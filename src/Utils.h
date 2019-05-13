//
//
// File: Utils.h
//

#ifndef UTILS_H_
#define UTILS_H_

#include <string>
#include <cstring>
#include <sstream>
#include <stdarg.h>
#include <stdio.h>
#include <sys/types.h>
#include <vector>

////// LOGGING MACROS
////// gcc recognizes a signature without variadic args: (verbosity, format) as well as
////// with: (vebosity, format, arg_1, arg_2, ... arg_n).  Other preprocessors may not.
////// To ensure compatibility, always provide at least one varg (which may be an empty string,
////// eg: (vebosity, format, "")

// PHIL_VERBOSE and PHIL_CONDITIONAL_VERBOSE print to the stout using Utils::phil_verbose
#ifdef PHILVERBOSE
#define PHIL_VERBOSE(verbosity, format, ...){\
  if ( Global::Verbose > verbosity ) {\
    Utils::phil_verbose(verbosity, "PHIL_VERBOSE: <%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_VERBOSE(verbosity, format, ...){}\

#endif
// PHIL_CONDITIONAL_VERBOSE prints to the stout if the verbose level is exceeded and the supplied conditional is true
#ifdef PHILVERBOSE
#define PHIL_CONDITIONAL_VERBOSE(verbosity, condition, format, ...){\
  if ( Global::Verbose > verbosity && condition ) {\
    Utils::phil_verbose(verbosity, "PHIL_CONDITIONAL_VERBOSE: <%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_CONDITIONAL_VERBOSE(verbosity, condition, format, ...){}\

#endif

// PHIL_STATUS and PHIL_CONDITIONAL_STATUS print to Global::Statusfp using Utils::phil_verbose_statusfp
// If Global::Verbose == 0, then abbreviated output is produced
#ifdef PHILSTATUS
#define PHIL_STATUS(verbosity, format, ...){\
  if ( verbosity == 0 && Global::Verbose <= 1 ) {\
    Utils::phil_verbose_statusfp(verbosity, format, ## __VA_ARGS__);\
  }\
  else if ( Global::Verbose > verbosity ) {\
    Utils::phil_verbose_statusfp(verbosity, "PHIL_STATUS: <%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_STATUS(verbosity, format, ...){}\

#endif
// PHIL_CONDITIONAL_STATUS prints to Global::Statusfp if the verbose level is exceeded and the supplied conditional is true
#ifdef PHILSTATUS
#define PHIL_CONDITIONAL_STATUS(verbosity, condition, format, ...){\
  if ( verbosity == 0 && Global::Verbose <= 1 && condition ) {\
    Utils::phil_verbose_statusfp(verbosity, format, ## __VA_ARGS__);\
  }\
  else if ( Global::Verbose > verbosity && condition ) {\
    Utils::phil_verbose_statusfp(verbosity, "PHIL_CONDITIONAL_STATUS: <%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_CONDITIONAL_STATUS(verbosity, condition, format, ...){}\

#endif

// PHIL_DEBUG prints to Global::Statusfp using Utils::phil_verbose_statusfp
#ifdef PHILDEBUG
#define PHIL_DEBUG(verbosity, format, ...){\
  if ( Global::Debug >= verbosity ) {\
    Utils::phil_verbose_statusfp(verbosity, "PHIL_DEBUG: <%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_DEBUG(verbosity, format, ...){}\

#endif

// PHIL_WARNING and PHIL_CONDITIONAL_WARNING print to both stdout and the Global::ErrorLogfp using Utils::phil_warning
#ifdef PHILWARNING
#define PHIL_WARNING(format, ...){\
  Utils::phil_warning("<%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
}

#else
#define PHIL_WARNING(format, ...){}\

#endif
// PHIL_CONDITIONAL_WARNING prints only if supplied conditional is true
#ifdef PHILWARNING
#define PHIL_CONDITIONAL_WARNING(condition, format, ...){\
  if (condition) {\
    Utils::phil_warning("<%s, LINE:%d> " format, __FILE__, __LINE__, ## __VA_ARGS__);\
  }\
}

#else
#define PHIL_CONDITIONAL_WARNING(condition, format, ...){}\

#endif


using namespace std;

namespace Utils {
void phil_abort(const char* format,...);
void phil_warning(const char* format,...);
void phil_open_output_files(char * directory, int run);
void phil_make_directory(char * directory);
void phil_end();
void phil_print_wall_time(const char* format, ...);
void phil_start_timer();
void phil_start_timer(time_t * lap_start_time);
void phil_start_day_timer();
void phil_print_day_timer(int day);
void phil_print_finish_timer();
void phil_print_lap_time(const char* format, ...);
void phil_print_lap_time(time_t * start_lap_time, const char* format, ...);
void phil_verbose(int verbosity, const char* format, ...);
void phil_verbose_statusfp(int verbosity, const char* format, ...);
void phil_log(const char* format, ...);
void phil_report(const char* format, ...);
FILE *phil_open_file(char * filename);
void get_phil_file_name(char * filename);
void phil_print_resource_usage(int day);
void replace_csv_missing_data(char *out_str, char* in_str, const char * replacement);
void get_next_token(char * out_string, char ** input_string);
void delete_char(char *s, char c, int maxlen);
void normalize_white_space(char *s);
char* strsep(char** stringp, const char* delim);

class Tokens {
    std::vector< std::string > tokens;

  public:

    std::string & back() {
        return tokens.back();
    }
    std::string & front() {
        return tokens.front();
    }

    void clear() {
        tokens.clear();
    }
    void push_back(std::string str) {
        tokens.push_back(str);
    }
    void push_back(const char * cstr) {
        tokens.push_back(std::string(cstr));
    }
    const char * operator[](int i) const {
        return tokens[ i ].c_str();
    }
    int fill_empty_with(const char * c) {
        std::vector< std::string >::iterator itr = tokens.begin();
        for (; itr != tokens.end(); ++itr) {
            if ((*itr).empty())(*itr).assign(c);
        }
    }
    size_t size() const {
        return tokens.size();
    }
    const char * join(const char * delim) {
        if (tokens.size() == 0) {
            return "";
        } else {
            std::stringstream ss;
            ss << tokens[ 0 ];
            for (int i = 1; i < tokens.size(); ++i) {
                ss << delim << tokens[ i ];
            }
            return ss.str().c_str();
        }
    }
};


Tokens & split_by_delim(const std::string & str,
                        const char delim, Tokens & tokens,
                        bool collapse_consecutive_delims = true);

Tokens split_by_delim(const std::string & str,
                      const char delim, bool collapse_consecutive_delims = true);

Tokens & split_by_delim(const char * str,
                        const char delim, Tokens & tokens,
                        bool collapse_consecutive_delims = true);

Tokens split_by_delim(const char * str,
                      const char delim, bool collapse_consecutive_delims = true);

}

#endif /* UTILS_H_ */
