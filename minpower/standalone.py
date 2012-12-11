import os
import pandas as pd
from pandas import Series, DataFrame
from commonscripts import gen_time_dataframe
from config import user_config

from schedule import TimeIndex
from get_data import parse_standalone


def wipe_storage():
    try: 
        os.remove(user_config.store_filename)
        print 'wipe storage'
    except OSError: pass
    

def get_storage():
    return pd.HDFStore(user_config.store_filename)

        
def store_times(tstage, storage=None):
    if storage is None:
        storage = get_storage()
    storage['times'] = tstage.strings
    return storage
        
def store_state(power_system, times, sln=None):
    storage = get_storage()
    generators = power_system.generators()
   
    if sln is None: 
        # pre-first stage
        stages = len(times) #stage_times
        t = [times[0].initialTime]
        
        storage['power'] = gen_time_dataframe(generators, t, 
            values = [[gen.initial_power for gen in generators]])
        storage['status'] = gen_time_dataframe(generators, t, 
            values = [[gen.initial_status for gen in generators]])
        storage['hrsinstatus'] = gen_time_dataframe(generators, t, 
            values = [[gen.initial_status_hours for gen in generators]])

        storage['load_shed'] = Series()
        storage['expected_cost'] = DataFrame()
        storage['observed_cost'] = DataFrame()
        storage['expected_status'] = DataFrame()
        storage['expected_power'] = DataFrame()
        
        # per-stage results 
        storage['solve_time'] = Series(index=range(stages))
        
        # store configuration
        # store stage initial state
        user_config._int_overlap = times[0]._int_overlap
        user_config._int_division = times[0]._int_division
        storage['configuration'] = Series(user_config)        
    else:
        stg = sln.stage_number
        table_append(storage, 'power', sln.generators_power)
        table_append(storage, 'status', sln.generators_status)
        table_append(storage, 'load_shed', sln.load_shed_timeseries)
        
        tEnd = times.last_non_overlap()
        storage['hrsinstatus'] = gen_time_dataframe(generators, [tEnd], 
            values = [
                [gen.finalstatus['hoursinstatus'] for gen in generators]
            ])
        
        _add_tbl_val(storage, 'solve_time', stg, sln.solve_time)                
        
        if sln.is_stochastic or user_config.deterministic_solve:
            table_append(storage, 'observed_cost', sln.observed_totalcost)
            table_append(storage, 'expected_cost', sln.expected_totalcost)
            table_append(storage, 'expected_power', sln.expected_power)
            table_append(storage, 'expected_status', sln.expected_status)
        else:
            table_append(storage, 'expected_cost', sln.totalcost_generation)
    return storage
    
def load_state():
    storage = get_storage()
    user_config.update(storage['configuration'].to_dict())
    
    startidx = int(storage['times'][0].strip('t'))
    times = TimeIndex(storage['times'].index, startidx)
    times._int_overlap = user_config._int_overlap
    times._int_division = user_config._int_division
    # create power_system
    power_system, times, scenario_tree = parse_standalone(times)
    generators = power_system.generators()
    
    # set up initial state
    t = times.initialTime
    
    
    for gen in generators: 
        g = str(gen)
        gen.set_initial_condition(t, 
            P=storage['power'][g][t],
            u=storage['status'][g][t],
            hoursinstatus=storage['hrsinstatus'][g][t])
    
    return power_system, times, scenario_tree

def repack_storage():
    '''do some clean-up compression on that ballooning storage'''
    # http://stackoverflow.com/questions/13089359/mystery-when-storing-a-dataframe-containing-strings-in-hdf-with-pandas
    os.system('ptrepack {f} copy{f}; mv copy{f} {f};'.format(
        f=user_config.store_filename))
    
def _add_tbl_val(storage, tablename, index, value):
    tbl = storage[tablename]
    tbl[index] = value
    storage[tablename] = tbl
    
def table_append(store, name, newvals):
    store[name] = store[name].append(newvals)
    return
