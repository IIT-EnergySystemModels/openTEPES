import math
import copy

class PFMError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

#default values are extra data in 2000 bus benchmarks
class Bus(object):
    def __init__(self, bus_i, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin, lam_P=None, lam_Q=None, mu_Vmax=None, mu_Vmin=None):
        self.bus_i = int(bus_i)
        self.type = int(type)
        self.Pd = float(Pd)
        self.Qd = float(Qd)
        self.Gs = float(Gs)
        self.Bs = float(Bs)
        self.area = int(area)
        self.Vm = float(Vm)
        self.Va = float(Va)
        self.baseKV = float(baseKV)
        self.zone = int(zone)
        self.Vmax = float(Vmax)
        self.Vmin = float(Vmin)
        
    def __str__(self):
        data = [self.bus_i, self.type, self.Pd, self.Qd, self.Gs, self.Bs, self.area, self.Vm, self.Va, self.baseKV, \
                self.zone, self.Vmax, self.Vmin]
        return ' '.join([str(x) for x in data])
        
    def make_per_unit(self, baseMVA):
        return Bus(self.bus_i, self.type, self.Pd/baseMVA, self.Qd/baseMVA, \
                   self.Gs/baseMVA, self.Bs/baseMVA, self.area, self.Vm, self.Va, \
                   self.baseKV, self.zone, self.Vmax, self.Vmin);

    def make_radians(self):
        return Bus(self.bus_i, self.type, self.Pd, self.Qd, \
                   self.Gs, self.Bs, self.area, self.Vm, self.Va, \
                   self.baseKV, self.zone, self.Vmax, self.Vmin);


#default values are extra data in 2000 bus benchmarks
class Generator(object):
    def __init__(self, idx, bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1=0, Pc2=0, Qc1min=0, Qc1max=0, Qc2min=0, Qc2max=0, ramp_agc=0, ramp_10=0, ramp_30=0, ramp_q=0, apf=0, mu_Pmax=None, mu_Pmin=None, mu_Qmax=None, mu_Qmin=None):
        self.idx = int(idx)
        self.bus = int(bus)
        self.Pg = float(Pg)
        self.Qg = float(Qg)
        self.Qmax = float(Qmax)
        self.Qmin = float(Qmin)
        self.Vg = float(Vg)
        self.mBase = float(mBase)
        self.status = int(status)
        self.Pmax = float(Pmax)
        self.Pmin = float(Pmin)
        self.Pc1 = float(Pc1)
        self.Pc2 = float(Pc2)
        self.Qc1min = float(Qc1min)
        self.Qc1max = float(Qc1max)
        self.Qc2min = float(Qc2min)
        self.Qc2max = float(Qc2max)
        self.ramp_agc = float(ramp_agc)
        self.ramp_10 = float(ramp_10)
        self.ramp_30 = float(ramp_30)
        self.ramp_q = float(ramp_q)
        self.apf = float(apf)

    def __str__(self):
        data = [self.idx, self.bus, self.Pg, self.Qg, self.Qmax, self.Qmin, self.Vg, self.mBase, self.status, self.Pmax, self.Pmin, self.Pc1, \
                self.Pc2, self.Qc1min, self.Qc1max, self.Qc2min, self.Qc2max, \
                self.ramp_agc, self.ramp_10, self.ramp_30, self.ramp_q, self.apf]
        return ' '.join([str(x) for x in data])

    def make_per_unit(self, baseMVA):
        return Generator(self.idx, self.bus, self.Pg/baseMVA, self.Qg/baseMVA, self.Qmax/baseMVA, self.Qmin/baseMVA, \
                      self.Vg, self.mBase, self.status, self.Pmax/baseMVA, self.Pmin/baseMVA, self.Pc1, self.Pc2, \
                      self.Qc1min, self.Qc1max, self.Qc2min, self.Qc2max, \
                      self.ramp_agc, self.ramp_10, self.ramp_30, self.ramp_q, self.apf);
                      
    def make_radians(self):
        return Generator(self.idx, self.bus, self.Pg, self.Qg, self.Qmax, self.Qmin, \
                    self.Vg, self.mBase, self.status, self.Pmax, self.Pmin, self.Pc1, self.Pc2, \
                    self.Qc1min, self.Qc1max, self.Qc2min, self.Qc2max, \
                    self.ramp_agc, self.ramp_10, self.ramp_30, self.ramp_q, self.apf);




class Branch(object):
    def __init__(self, idx, fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin=-360, angmax=360, Pf=None, Qf=None, Pt=None, Qt=None, mu_Sf=None, mu_St=None, mu_angmin=None, mu_angmax=None, radians=False):
        self.idx = int(idx)
        self.radians = radians
        self.fbus = int(fbus)
        self.tbus = int(tbus)
        self.r = float(r)
        self.x = float(x)
        self.b = float(b)
        self.rateA = float(rateA)
        self.rateB = float(rateB)
        self.rateC = float(rateC)
        self.ratio = float(ratio)
        self.angle = float(angle)
        self.status = int(status)
        self.angmin = float(angmin)
        self.angmax = float(angmax)
    
    def __str__(self):
        data = [self.idx, self.fbus, self.tbus, self.r, self.x, self.b, self.rateA, self.rateB, self.rateC, \
                self.ratio, self.angle, self.status, self.angmin, self.angmax, self.radians]
        return ' '.join([str(x) for x in data])
    
    def make_per_unit(self, baseMVA):
        return Branch(self.idx, self.fbus, self.tbus, self.r, self.x,  self.b, \
                      self.rateA/baseMVA, self.rateB/baseMVA, self.rateC/baseMVA, \
                      self.ratio, self.angle, self.status, self.angmin, self.angmax);
    
    def make_radians(self):
        if self.radians:
            return Branch(self.idx, self.fbus, self.tbus, self.r, self.x,  self.b, \
                        self.rateA, self.rateB, self.rateC, \
                        self.ratio, self.angle, self.status, self.angmin, self.angmax, radians=True);
        else:
            return Branch(self.idx, self.fbus, self.tbus, self.r, self.x,  self.b, \
                        self.rateA, self.rateB, self.rateC, \
                        self.ratio, math.radians(self.angle), self.status, math.radians(self.angmin), math.radians(self.angmax), radians=True);
    
    def replace_phase_angle_diffrence(self, delta):
        if self.radians:
            return Branch(self.idx, self.fbus, self.tbus, self.r, self.x,  self.b, \
                    self.rateA, self.rateB, self.rateC, \
                    self.ratio, self.angle, self.status, -delta, delta, radians=self.radians);
        else:
            return Branch(self.idx, self.fbus, self.tbus, self.r, self.x,  self.b, \
                    self.rateA, self.rateB, self.rateC, \
                    self.ratio, self.angle, self.status, -math.degrees(delta), math.degrees(delta), radians=self.radians);

    def update_line_limits(self, from_Vmax, to_Vmax):
        assert(self.radians)
        # TODO assumes all values are in per unit! See issue #2 in Github

        # compute value thermal limit UB
        theta_max = max(abs(self.angmin), abs(self.angmax))

        r = self.r
        x = self.x
        g =  r / (r**2 + x**2)
        b = -x / (r**2 + x**2)

        y_mag = math.sqrt(g**2 + b**2)

        m_Vmax = max(from_Vmax, to_Vmax)

        c_max = math.sqrt(from_Vmax**2 + to_Vmax**2 - 2*from_Vmax*to_Vmax*math.cos(theta_max))

        rate_ub = y_mag*m_Vmax*c_max

        if self.rateA == 0 or self.rateA > rate_ub:
            print('warning: on line %d from bus %d to bus %d updated rateA: %f => %f' % (self.idx, self.fbus, self.tbus, self.rateA, rate_ub))
            self.rateA = rate_ub




class GeneratorCost(object): 
    def __init__(self, idx, type, startup, shutdown, n, c2, c1, c0):
        self.idx = int(idx)
        self.type = int(type)
        self.startup = float(startup)
        self.shutdown = float(shutdown)
        self.n = int(n)
        self.c2 = float(c2)
        self.c1 = float(c1)
        self.c0 = float(c0)
    
    def __str__(self):
        data = [self.idx, self.type, self.startup, self.shutdown, self.n, self.c2, self.c1, self.c0]
        return ' '.join([str(x) for x in data])
    
    def make_per_unit(self, baseMVA):
        return GeneratorCost(self.idx, self.type, self.startup, self.shutdown, self.n, self.c2*baseMVA**2, self.c1*baseMVA, self.c0);
    
    def make_radians(self):
        return GeneratorCost(self.idx, self.type, self.startup, self.shutdown, self.n, self.c2, self.c1, self.c0);


from collections import namedtuple
arc = namedtuple("arc", ['f','t'])

class Admittance(complex):
    def __init__(self, *p, **k):
        super(Admittance,self).__init__(*p, **k)
        setattr(self, 'g', self.real)
        setattr(self, 'b', self.imag)
        
class Transformer(complex):
    def __init__(self, tr, sa):
        super(Transformer,self).__init__(tr*math.cos(sa), tr*math.sin(sa))
        setattr(self, 'c', self.real)
        setattr(self, 'd', self.imag)
        setattr(self, 'tr', abs(self))
        setattr(self, 'sa', math.atan(self.imag/self.real))
        
    


class YBus(dict):
    
    def __init__(self, case):
        #Z = {b:complex(b.r, b.x) for b in case.branch}
        #Y = {b:Admittance(1/z) for b,z in Z.iteritems()}
        self.neighbors = {x.bus_i:set() for x in case.bus}
        self.branch_admittance = {}
        
        for b in case.branch:
            #if b.angle != 0.0:
                #print b.ratio*math.sin(b.angle)
                #raise PFMError('ybus transformation currently does not support phase shifting transformers')
            z = complex(b.r, b.x)
            y = 1/z
            line_charge = complex(0, b.b)
            tap = Transformer(1, 0)
            if b.ratio != 0.0 or b.angle != 0:
                tap = Transformer(b.ratio, b.angle)
            
            f = Admittance((y+line_charge/2)/tap.tr)
            t = Admittance((y)/tap.conjugate())
            
            rf = Admittance(y+line_charge/2)
            rt = Admittance((y)/tap)
            
            self[(b.fbus,b.tbus,b.idx)] = arc(f,t)
            self[(b.tbus,b.fbus,b.idx)] = arc(rf,rt)
            
            self.branch_admittance[(b.fbus,b.tbus,b.idx)] = Admittance(y)
            self.branch_admittance[(b.tbus,b.fbus,b.idx)] = Admittance(y)
            
            self.neighbors[b.fbus].add((b.fbus,b.tbus,b.idx))
            self.neighbors[b.tbus].add((b.tbus,b.fbus,b.idx))
            


class Case(object):
    def __init__(self, name=None, baseMVA=None, bus=None, gen=None, branch=None, gencost=None):
        self.name = name
        self.version = 2
        self.baseMVA = baseMVA
        self.refbus = None
        self.bus = bus
        self.gen = gen
        self.branch = branch
        self.gencost = gencost

    def __str__(self):
        tmp = self.name+' '+str(self.version)+' '+str(self.baseMVA)+'\n'
        tmp += '\n'
        
        tmp += 'Buses:\n'
        tmp += '\n'.join([str(x) for x in self.bus])
        tmp += '\n \n'
        
        tmp += 'Generators:\n'
        tmp += '\n'.join([str(x) for x in self.gen])
        tmp += '\n \n'
        
        tmp += 'Generator Costs:\n'
        tmp += '\n'.join([str(x) for x in self.gencost])
        tmp += '\n \n'
        
        tmp += 'Branches:\n'
        tmp += '\n'.join([str(x) for x in self.branch])
        
        return tmp
        
        
    def check(self):
        if self.name == None:
            raise PFMError('case has no name')
        if self.baseMVA == None:
            raise PFMError('case has no name')
        if self.bus == None:
            raise PFMError('case has no buses')
        if self.gen == None:
            raise PFMError('case has no generators')
        if self.branch == None:
            raise PFMError('case has no branches')
        if self.gencost == None:
            raise PFMError('case has no generator cost data')
        
        if len(self.gencost) != len(self.gen):
            raise PFMError('number of gencost items does not match the number of generators')
        
        
        for g in self.gen:
            if g.status == 0:
                raise PFMError('status of 0 not currently supported')
        
        for b in self.branch:
            if b.status == 0:
                raise PFMError('status of 0 not currently supported')
    
    
    def make_per_unit(self):
        bus = [x.make_per_unit(self.baseMVA) for x in self.bus]
        gen = [x.make_per_unit(self.baseMVA) for x in self.gen]
        branch = [x.make_per_unit(self.baseMVA) for x in self.branch]
        gencost = [x.make_per_unit(self.baseMVA) for x in self.gencost]
        
        #return Case(self.name+'_pu', 1.0, bus, gen, branch, gencost);
        return Case(self.name, 1.0, bus, gen, branch, gencost);
    
    
    def make_radians(self):
        bus = [x.make_radians() for x in self.bus]
        gen = [x.make_radians() for x in self.gen]
        branch = [x.make_radians() for x in self.branch]
        gencost = [x.make_radians() for x in self.gencost]
    
        #return Case(self.name+'_rad', self.baseMVA, bus, gen, branch, gencost);
        return Case(self.name, self.baseMVA, bus, gen, branch, gencost);
    
    
    def replace_phase_angle_difference(self, delta=math.pi/12):
        if delta < 0.0:
            raise PFMError('phase angle difference is out of range. The value should be a positive number')
        if delta > 2*math.pi:
            raise PFMError('phase angle difference is out of range. Note, the value should be povided in raidans')
        
        bus = [copy.deepcopy(x) for x in self.bus]
        gen = [copy.deepcopy(x) for x in self.gen]
        branch = [x.replace_phase_angle_diffrence(delta) for x in self.branch]
        gencost = [copy.deepcopy(x) for x in self.gencost]
    
        #return Case(self.name+'_pad', self.baseMVA, bus, gen, branch, gencost);
        return Case(self.name, self.baseMVA, bus, gen, branch, gencost);

    def update_line_limits(self):
        bus = [copy.deepcopy(x) for x in self.bus]
        gen = [copy.deepcopy(x) for x in self.gen]
        branch = [copy.deepcopy(x) for x in self.branch]
        gencost = [copy.deepcopy(x) for x in self.gencost]

        bus_lookup = {x.bus_i:x for x in bus}
        for b in branch:
            from_bus = bus_lookup[b.fbus]
            to_bus = bus_lookup[b.tbus]
            b.update_line_limits(from_bus.Vmax, to_bus.Vmax)

        return Case(self.name, self.baseMVA, bus, gen, branch, gencost);
    
    def remove_status_zero(self):
        off_bus = set([x.bus_i for x in self.bus if x.type == 4])
        if len(off_bus):
            print("Warning: removing turned off buses:",off_bus)

        bus = [copy.deepcopy(x) for x in self.bus if not x.bus_i in off_bus]
        off_gen = [i for i,x in enumerate(self.gen) if x.status == 0 or x.bus in off_bus]
        on_gen  = [i for i,x in enumerate(self.gen) if x.status == 1 and not x.bus in off_bus]
        
        if len(off_gen) > 0:
            print("Warning: removing turned off gens:",off_gen)
            gen = [copy.deepcopy(self.gen[i]) for i in on_gen]
            gencost = [copy.deepcopy(self.gencost[i]) for  i in on_gen]
        else:
            gen = [copy.deepcopy(x) for x in self.gen]
            gencost = [copy.deepcopy(x) for x in self.gencost]
            
        off_branch = [i for i,x in enumerate(self.branch) if x.status == 0 or x.fbus in off_bus or x.tbus in off_bus]
        on_branch = [i for i,x in enumerate(self.branch) if x.status == 1 and not x.fbus in off_bus and not x.tbus in off_bus]
        
        if len(off_branch) > 0:
            print("Warning: removing turned off lines:",off_branch)
            branch = [copy.deepcopy(self.branch[i]) for i in on_branch]
        else:    
            branch = [copy.deepcopy(x) for x in self.branch]
        
        #return Case(self.name+'_status-1', self.baseMVA, bus, gen, branch, gencost);
        return Case(self.name, self.baseMVA, bus, gen, branch, gencost);


    def ref_bus(self):
        if self.refbus == None:
            for x in self.bus:
                if x.type == 3:
                    assert(self.refbus == None)
                    self.refbus = x
        return self.refbus

    def make_ybus(self):
        return YBus(self);
        
    def bus_ids(self):
        return set(x.bus_i for x in self.bus)
        
    def gen_ids(self):
        #return set(x.bus for x in self.gen)
        return set(x.idx for x in gen)
        
    def branch_ids(self):
        return set((x.tbus,x.fbus,x.idx) for x in self.branch)
    
    def branch_lookup(self):
        return {(x.tbus,x.fbus,x.idx):x for x in self.branch}
    
    def bus_lookup(self):
        return {x.bus_i:x for x in self.bus}
        
    def gen_lookup(self):
        gens = {x.bus_i:set() for x in self.bus}
        for g in self.gen:
            gens[g.bus].add(gen.idx)
        return gens
    
        