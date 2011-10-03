import logging

from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator
from minpower.optimization import value

singletime=schedule.just_one_time()

def make_single_bus(generators,loads):
    singlebus=powersystems.Bus()
    singlebus.generators=generators
    singlebus.loads=loads
    return [singlebus]    

def make_cheap_gen(**kwargs):
    return Generator(name='cheap gen', costcurvestring='10P', **kwargs)
def make_mid_gen(**kwargs):
    return Generator(name='middle-range gen', costcurvestring='20P', **kwargs)    
def make_expensive_gen(**kwargs):
    return Generator(name='expensive gen', costcurvestring='30P', **kwargs)    
def make_load(Pd=200,Pdt=None):
    if Pdt is None: 
        return dict(load=[powersystems.Load_Fixed(P=Pd)],times=singletime)
    else: 
        times = schedule.make_times_basic(N=len(Pdt))
        #logging.critical([unicode(t) for t in times])
        sched = schedule.Schedule(times=times, P=Pdt)
        return dict(load=[powersystems.Load(schedule=sched)],times=times)

def solve_problem(generators,load,  gen_init=None, lines=None, solver=config.optimization_solver):
    if lines is None: lines=[]
    
    times=load['times']
    if len(times)>0: 
        for g,gen in enumerate(generators): 
            if gen_init is None: gen.setInitialCondition(times.initialTime)
            else:                gen.setInitialCondition(times.initialTime, **gen_init[g])
            gen.index=g
        
    buses=make_single_bus(generators,loads=load['load'])
    problem=solve.create_problem(buses,lines,times)
    problem.solve(solver=solver)
    if problem.solved:
        for g in generators: g.update_vars(times,problem)
    else:
        #logging.critical( [g.power[times.initialTime] for g in generators] )
        problem.write('problem.lp')
        raise optimization.OptimizationError('infeasible problem, wrote to problem.lp')
    return problem,times