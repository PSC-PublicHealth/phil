import pandas as pd
import numpy as np
import ujson, yaml, time, bz2, gzip, os, re
try:
    import lzma
except ImportError as e:
    import backports.lzma as lzma
from collections import OrderedDict, defaultdict
#import pyximport
#pyximport.install(reload_support=True)
#import cyprinev.count_events as count_events
import phil_output_extractor.count_events as count_events
import logging
import joblib
from numpy import arange
import coloredlogs

logging.basicConfig(level=logging.INFO, format='[%(name)s] %(asctime)s %(message)s')
log = logging.getLogger(__name__)
coloredlogs.install(level='INFO')

class Timer():
    def __init__(self):
        self.tic = time.time()
    def __call__(self):
        toc = time.time()
        t = '%0.1f' % (toc - self.tic)
        self.tic = toc
        return t

def AutoDetectFile(filename):
    filetypes = [
            ('bz2', bz2.BZ2File, '\x42\x5a\x68'),
            ('gzip', gzip.GzipFile, '\x1f\x8b\x08'),
            ('lzma', lzma.LZMAFile, '\xfd7zXZ\x00')]
    for typename, fileopen, magic in filetypes:
        try:
            with open(filename, 'r') as f:
                if f.read(len(magic)) != magic:
                    raise Exception()
            f = fileopen(filename, 'r')
            log.info('Opened %s as %s' % (filename, typename))
            return f
        except:
            log.debug('Unsuccessfully tried to open as %s' % typename)
    log.info('Opening as plain text file')
    f = open(filename, 'r')
    return f

def expand_config(config):
    x = {}
    for k,c in config.iteritems():
        if c is not None and 'intervals' in c:
            x[k] = []
            if isinstance(c['intervals'], list):
                for i in c['intervals']:
                    if isinstance(i, dict):
                        x[k].extend(arange(i['from'], i['to']+i['by'], i['by']))
                    else:
                        x[k].append(i)
            else:
                # intervals is just the number of bins
                x[k] = c['intervals']
        else:
            x[k] = None
    return(x)

###############################################################################

DTYPE = np.uint32
NA = DTYPE(-1)

class OutputCollection(object):

    @property
    def state_dict(self):
        return dict(N = 'number of individuals', S = 'susceptible',
                E = 'exposed', I = 'infectious', Y = 'symptomatic',
                R = 'recovered', IS = 'infectious and symptomatic')
        
    @property
    def population_dict(self):
        return dict(race = 'race', age = 'age', gender = 'sex')

    @property
    def infection_dict(self):
        return dict(place_type = 'place_type')

    @property
    def household_dict(self):
        return dict(income = 'hh_income', stcotrbg = 'stcotrbg',
                stcotr = 'stcotr', location = 'apollo_location_code',
                latitude = 'latitude', longitude = 'longitude')

    @property
    def default_config(self):
        d = os.path.dirname(os.path.abspath(__file__))
        f = os.path.join(d, 'default_group_config.yaml')
        return open(f, 'r')

    @property
    def apollo_location_lookup_filename(self):
        d = os.path.dirname(os.path.abspath(__file__))
        f = os.path.join(d, 'ApolloLocationCode.to.FIPSstcotr.csv')
        return f


    @property
    def event_map(self):
        return OrderedDict([('exposed',0), ('infectious',1), ('symptomatic',2),
            ('recovered',3), ('susceptible',4), ('vaccine',5), ('vaccine_day',6)])

    @property
    def state_map(self):
        return OrderedDict([('N_i',0),('N_p',1),('S_i',2),('S_p',3),('E_i',4),
            ('E_p',5),('I_i',6),('I_p',7),('Y_i',8),('Y_p',9),('R_i',10),
            ('R_p',11),('IS_i',12),('IS_p',13),('V_i',14),('V_p',15)])

    def __init__(self, popdir, persist_synth_pop=True):
        log.debug('read default group config: %s' % [
            str(yaml.load(self.default_config))])
        self.persist = persist_synth_pop
        self.popdir = popdir
        self.load_popfiles()

    def load_popfiles(self):
        base = os.path.basename(self.popdir)
        timer = Timer()

        popfile = os.path.join(self.popdir, '%s_synth_people.txt' % base) 
        try:
            self.population = pd.read_hdf('%s.h5' % popfile)
            log.info('Read persisted population from hdf5')
        except:
            self.population = pd.read_csv(popfile, low_memory=False)
            self.population.age += np.random.uniform(low=0.0, high=1.0,
                    size=len(self.population.index))
            #self.population.reset_index(inplace=True)
            #self.population['person'] = self.population.index
            self.population.rename(
                    columns={
                        'p_id': 'person',
                        'sp_id': 'person',
                        'sp_hh_id': 'hh_id'},
                    inplace=True)
            if self.persist:
                try:
                    self.population.to_hdf('%s.h5' % popfile,
                            key='population', mode='w')
                    log.info('Persisted population to hdf5')
                except:
                    log.info('Unable to persist population file as hdf5!')
        log.info('read population in %s seconds' % timer())

        self.households = pd.read_csv(
                os.path.join(self.popdir, '%s_synth_households.txt' % base))
        self.households.reset_index()
        self.households.rename(columns={'sp_id': 'hh_id'}, inplace=True)
        self.households['stcotr'] = (self.households.stcotrbg/10).astype(np.int64)
        apollo_locations = pd.read_csv(self.apollo_location_lookup_filename)
        apollo_locations.reset_index(level=0, inplace=True)
        self.households = pd.merge(self.households, apollo_locations,
            on='stcotr', how='inner', suffixes=('','_'))
        log.info('read households in %s seconds' % timer())
        self.workplaces = pd.read_csv(
                os.path.join(self.popdir, '%s_workplaces.txt' % base))
        log.info('read workplaces in %s seconds' % timer())
        self.schools = pd.read_csv(
                os.path.join(self.popdir, '%s_schools.txt' % base))
        log.info('read schools in %s seconds' % timer())

    def query_population(self, groupby_attributes): 
    
        _rev_population_dict = {self.population_dict[x]:x for x in \
                groupby_attributes if x in self.population_dict}
        
        _rev_population_dict.update({'person':'person'})
        
        _rev_household_dict = {self.household_dict[x]:x for x in \
                groupby_attributes if x in self.household_dict}

        _population = pd.merge(self.population[_rev_population_dict.keys() + ['hh_id']],
                               self.households[_rev_household_dict.keys() + ['hh_id']],
                               on='hh_id', suffixes=('', '.h'), how='inner',
                               copy=True)[_rev_population_dict.keys() + \
                                          _rev_household_dict.keys()]
        
        _population.rename(columns=_rev_population_dict, inplace=True, copy=False)
        _population.rename(columns=_rev_household_dict, inplace=True, copy=False)

        for k in groupby_attributes:
            if k not in list(_population.columns) and k not in self.infection_dict:
                raise Exception('Unable to group by key: %s' % k)
        
        return _population
    
    def bin_columns(self, d, groupconfig):
        for g,i in expand_config(groupconfig).iteritems():
            if i is not None:
                if isinstance(i, list):
                    d[g] = pd.cut(d[g], bins=i, right=False, include_lowest=True)
                else:
                    d[g] = pd.cut(d[g], bins=i)

        return(d)

    def apply_count_events(self, events, groupconfig):
        timer = Timer()
        group_by_keys = groupconfig.keys()

        d_query_pop = self.query_population(group_by_keys)
        log.info('Extracted groups from population data in %s seconds' % timer())
        
        d = pd.merge(events['infection'], d_query_pop,
                     on='person', how='right', suffixes=('','_')
                    ).sort_values(group_by_keys).reset_index(drop=True)
        d = self.bin_columns(d, groupconfig)

        if 'vaccination' not in events:
            d_vacc = pd.DataFrame(dict(person=[], vaccine=[], vaccine_day=[]))
        else:
            d_vacc = events['vaccination']

        d = pd.merge(d, d_vacc, on='person', how='left')
        d = d[self.event_map.keys() + group_by_keys + ['person']]
        d[self.event_map.keys()] = d[self.event_map.keys()].fillna(NA).apply(
                lambda x: x.astype(DTYPE), axis=0)
        n_days = d.recovered[d.recovered != NA].max() + 1

        def convert_counts_array(g):
            a = count_events.get_counts_from_group(g[self.event_map.keys()].values.astype(np.uint32),
                                                   np.uint32(n_days),
                                                   self.event_map, self.state_map)
            df = pd.DataFrame(
                    np.asarray(a), columns=self.state_map.keys(),
                    index=pd.Index(data=range(a.shape[0]), name='day'))
            #df.index.name = 'day'
            return df

        log.info('Merged events with population data in %s seconds' % timer())
        grouped_counts = d.groupby(group_by_keys).apply(convert_counts_array)
        # NOTE! NOTE! NOTE! This is a hack until proper support for multi-season
        # reporting can be added!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        del grouped_counts['N_p']
        N_p = pd.DataFrame(
                    {'N_p':d.groupby(group_by_keys).apply(lambda d: len(d.person.unique()))})
        grouped_counts = grouped_counts.join(N_p)
        grouped_counts.S_p = grouped_counts.N_p - grouped_counts.E_p - grouped_counts.R_p
        # NOTE! NOTE! NOTE!
        log.info('Tabulated grouped event counts in %s seconds' % timer())
        return grouped_counts 

    def read_event_report(self, filename):
        output_lists = defaultdict(list)
        timer = Timer()
        with AutoDetectFile(filename) as f:
            for line in f:
                j = ujson.loads(line)
                output_lists[j.pop('event')].append(j)
        
        log.info('Read %s events from %s in %s seconds' % (
            ', '.join(output_lists.keys()), filename, timer()))

        return {k:pd.DataFrame(v) for k,v in output_lists.iteritems()}

    def count_events(self, reportfiles, groupconfig=None):
        rep_num = 0
        for f in reportfiles:
            k_orig = f
            k_safe = '%d__%s' % (rep_num, re.sub(r'[-.+ ]', '_', os.path.basename(f)))
            events = self.read_event_report(f)
            counts = self.apply_count_events(events, groupconfig)
            yield({'key': k_safe, 'name': k_orig, 'counts': counts, 'events': events})
            rep_num += 1

    def write_event_counts_to_hdf5(self, reportfiles, outfile, groupconfig=None):
        hdf_outfile_name = '%s.h5' % outfile
        hdf = pd.HDFStore(path=hdf_outfile_name, mode='w', complib='zlib', complevel=5)
        keymap = []
        for d in self.count_events(reportfiles, groupconfig):
            timer = Timer()
            hdf.append(d['key'], d.pop('counts'))
            keymap.append(d)
            log.debug('Added %s to hdf5 file %s' % (ujson.dumps(d), hdf_outfile_name))
            log.info('Wrote counts to %s file in %s seconds' % (hdf_outfile_name, timer())) 
            #hdf.put('%s/name' % d['key'], d['name'])
            #hdf.put('%s/paramters' % d['key'], ujson.dumps(events['parameters']))
        hdf.close()
        return keymap

    def write_event_counts_to_csv(self, reportfiles, outfile, groupconfig=None,
            include_school_infections=False):

        csv_outfile_name = '%s.csv' % outfile
        if include_school_infections:
            self.init_school_infections(outfile)
        hdr = True
        keymap = []
        with open(csv_outfile_name, 'w') as f:
            for d in self.count_events(reportfiles, groupconfig):
                df = d.pop('counts')
                #df['key'] = d['key']
                df['name'] = d['name']
                df.reset_index().to_csv(f, index=False, header=hdr, mode='a')
                if include_school_infections:
                    self.write_school_infections(d.pop('events'), d['name'], hdr)            
                hdr = False
                keymap.append(d)
                log.info('Added %s to csv file %s' % (ujson.dumps(d), csv_outfile_name))
        return keymap

    def init_school_infections(self, outfile):
        log.warn('INITIALIZING SCHOOL INFECTIONS')
        self.school_outfile = open('%s_school_infections.csv' % outfile, 'w')

        self._schools = self.schools[['school_id','name','address','city',
            'zip','total','prek','kinder','gr01-gr12',
            'latitude','longitude']].reset_index()

    def write_school_infections(self, events, name, hdr):
        log.warn('WRITING SCHOOL INFECTIONS')

        school_infections = events['infection'].query(
                'place_type == 83 and place_label != "NULL"')[
                        ['place_label','infector','person', 'exposed']]

        school_infections['school_id'] = school_infections.place_label.str.extract(
                '\D(\d+)\D*')

        r = pd.merge(school_infections, self._schools, on='school_id')
        r['name'] = name
        r.rename(columns={'exposed': 'day'}, inplace=True)
        r.to_csv(self.school_outfile, index=False, header=hdr, mode='a') 

    def write_apollo_internal(self, reportfiles, outfile, groupconfig=None):
        log.info('Producing apollo output format')
        #outfile_name = '%s.apollo.csv.gz' % outfile
        outfile_name = '%s.apollo.h5' % outfile
        hdf = pd.HDFStore(path=outfile_name, mode='w', complib='zlib', complevel=4)

        def reshape_thin(d):
            ds = d.stack()
            return pd.DataFrame(ds[ds!=0])
        timer = Timer()
        d1 = pd.concat([reshape_thin(r['counts']) for r in self.count_events_apollo(reportfiles, groupconfig)],
                copy=False)
        log.info('Concatenated all realizations in %s seconds' % timer())
        d2 = d1.groupby(level=range(len(d1.index.levels)
            )).sum()
        del(d1)
        d2 /= float(len(reportfiles))
        d2.reset_index(inplace=True)
        log.info('Calculated mean values for all groups in %s seconds' % timer())
        d2.columns = [x for x in d2.columns[:-2]] + ['state_tuple','count']

        d3 = d2.state_tuple.str.split(':', expand=True)
        d3.columns = ['infection_state', 'disease_state']
        
        d2.drop('state_tuple', axis=1, inplace=True)
        
        for s in ['infection_state', 'disease_state']:
            d2[s] = d3[s].astype('category')
            d3.drop(s, axis=1, inplace=True)
        del(d3)

        if 'gender' in d2:
            d2['sex'] = d2.gender.apply(lambda x: 'M' if x==1 else 'F').astype('category')
            d2.drop('gender', axis=1, inplace=True)
        if 'age' in d2:
            d2.rename(columns={'age':'age_range_category_label'}, inplace=True)
        if 'location' in d2:
            d2.rename(columns={'location':'household_location_admin4'}, inplace=True)
        if 'income' in d2:
            d2.rename(columns={'income':'household_median_income_category_label'}, inplace=True)
        if 'vaccination_status' in d2:
            v_s_map = {0: 'noVaccination', 1: 'successfulVaccination'}
            d2.vaccination_status = d2.vaccination_status.apply(lambda x: v_s_map[x]).astype('category')

        log.info('Renamed/recast data table to apollo standard in %s seconds' % timer())

        d2.set_index([x for x in d2.columns if x != 'count'], inplace=True)
        log.info('Begin writing apollo output format to %s' % outfile_name)
        #d2.to_csv(outfile_name, compression='gzip')
        hdf.put('apollo_aggregated_counts', d2, format='table')
        hdf.close()
        log.info('Wrote apollo output format to disk in %s seconds' % timer())

    def write_galapagos(self, reportfiles, outfile, groupconfig=None):
        log.info('Producing galapagos output format')

        outfile_name = '%s.galapagos.h5' % outfile
        hdf = pd.HDFStore(path=outfile_name, mode='w', complib='zlib', complevel=4)

        def reshape_thin(d):
            if ('latent:asymptomatic' in d) & ('newly_latent:asymptomatic' in d):
                d['existing_latent:asymptomatic']=d['latent:asymptomatic']-d['newly_latent:asymptomatic']
            else:
                d['existing_latent:asymptomatic']=0
            ds = d.stack()
            return pd.DataFrame(ds[ds!=0])

        def add_file_index(df,ind):
            df['file_ind']=ind
            df['file_ind']=(df['file_ind']).astype(np.uint8)
            return df

        def make_csv_struct_from_orig_dataframe(df):
            d2 = pd.concat([pd.DataFrame(df['simulator_time']),pd.DataFrame(df['infection_state']),pd.DataFrame(df['count'])],axis=1)
            d2sum = d2.groupby(['simulator_time','infection_state']).sum()
            d2sum = d2sum.fillna(value=0)
            d2sum['count']=(d2sum['count']).astype(np.uint32)
            return d2sum

        timer = Timer()
        count_all=self.count_events_apollo(reportfiles,groupconfig)

        d1 = pd.concat([add_file_index(reshape_thin(r['counts']),r['file_ind']) for r in count_all],copy=False)
        log.info('Concatenated all realizations in %s seconds' % timer())

        d1.reset_index(inplace=True)
        d1.columns = [x for x in d1.columns[:-3]] + ['state_tuple','count','report_index']

        d3 = d1.state_tuple.str.split(':', expand=True)
        d3.columns = ['infection_state', 'disease_state']

        d1.drop('state_tuple', axis=1, inplace=True)
        for s in ['infection_state', 'disease_state']:
            d1[s] = d3[s].astype('category')
            d3.drop(s, axis=1, inplace=True)
        del(d3)

        if 'gender' in d1:
            d1['sex'] = d1.gender.apply(lambda x: 'M' if x==1 else 'F').astype('category')
            d1.drop('gender', axis=1, inplace=True)
        if 'age' in d1:
            d1.rename(columns={'age':'age_range_category_label'}, inplace=True)
        if 'location' in d1:
            d1.rename(columns={'location':'household_location_admin4'}, inplace=True)
        if 'income' in d1:
            d1.rename(columns={'income':'household_median_income_category_label'}, inplace=True)
        if 'vaccination_status' in d1:
            v_s_map = {0: 'noVaccination', 1: 'successfulVaccination'}
            d1.vaccination_status = d1.vaccination_status.apply(lambda x: v_s_map[x]).astype('category')

        log.info('Renamed/recast data table to galapagos standard in %s seconds' % timer())

        d2 = make_csv_struct_from_orig_dataframe(d1)
        d2.to_csv(outfile+'.galapagos.csv')
        log.info('Wrote CSV file of infection state counts to '+outfile+'.galapagos.csv in %s seconds' % timer())

        d1.set_index([x for x in d1.columns if x != 'count'], inplace=True)
        log.info('Begin writing galapagos output format to %s' % outfile_name)
        hdf.put('apollo_aggregated_counts', d1, format='table')
        hdf.close()
        log.info('Wrote galapagos output format to disk in %s seconds' % timer())



    def count_events_apollo(self, reportfiles, groupconfig=None):
        for f in reportfiles:
            k_ind = reportfiles.index(f)
            k_orig = os.path.basename(f)
            k_safe = re.sub(r'[-.+ ]', '_', k_orig)
            events = self.read_event_report(f)
            counts = self.apply_count_events_apollo(events, groupconfig)
            yield({'key': k_safe, 'name': k_orig, 'counts': counts, 'events': events,'file_ind':k_ind})

    def apply_count_events_apollo(self, events, groupconfig):
        timer = Timer()
        group_by_keys = groupconfig.keys()

        d_query_pop = self.query_population(group_by_keys)
        log.info('Extracted groups from population data in %s seconds' % timer())
        
        d = pd.merge(events['infection'], d_query_pop,
                     on='person', how='right', suffixes=('','_')
                    ).sort_values(group_by_keys).reset_index(drop=True)
        d = self.bin_columns(d, groupconfig)

        if 'vaccination' not in events:
            d_vacc = pd.DataFrame(dict(person=[], vaccine=[], vaccine_day=[]))
        else:
            d_vacc = events['vaccination']

        d = pd.merge(d, d_vacc, on='person', how='left')
        d = d[self.event_map.keys() + group_by_keys]
        d[self.event_map.keys()] = d[self.event_map.keys()].fillna(NA).apply(
                lambda x: x.astype(DTYPE), axis=0)
        n_days = d.recovered[d.recovered != NA].max() + 1

        def convert_counts_array(g):
            a = count_events.get_counts_from_group_apollo(
                    g[self.event_map.keys()].values.astype(np.uint32),
                    np.uint32(n_days), self.event_map, self.apollo_state_map)
            df = pd.DataFrame(
                    np.asarray(a), columns=self.apollo_state_map.keys()+['vaccination_status'],
                    index=pd.Index(
                        data=range(n_days) + range(n_days),
                        name='simulator_time'))
            df.set_index('vaccination_status', append=True, inplace=True)
            return df

        log.info('Merged events with population data in %s seconds' % timer())
        grouped_counts = d.groupby(group_by_keys).apply(convert_counts_array)
        log.info('Tabulated grouped event counts in %s seconds' % timer())
        return grouped_counts 

    @property
    def apollo_state_map(self):
        return OrderedDict([
            ('susceptible:recovery', 0),
            ('latent:asymptomatic', 1),
            ('infectious:symptomatic', 2),
            ('infectious:asymptomatic', 3),
            ('recovered:recovery', 4),
            ('newly_sick:symptomatic', 5),
            ('newly_sick:asymptomatic', 6),
            ('newly_latent:asymptomatic', 7)
            ])




















