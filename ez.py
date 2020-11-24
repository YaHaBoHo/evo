import random
import itertools
import math
import time


def clamp(v, vmin, vmax):
    return min(max(v, vmin), vmax)

def cdiv(a, b):
    return -(-a // b)

class MP():

    def __init__(self, x, y, cs):
        self.x = x
        self.y = y
        self.cs = cs
        self.cl = None
        self.etty = list()
        # intt
        self.clr()

    def rp(self):
        return (random.random() * self.x, random.random() * self.y)

    def clr(self):
        self.cl = [[
            [] for _cy in range(cdiv(self.y, self.cs))
        ] for _cx in range(cdiv(self.x, self.cs))]

    def ppl(self, cnt=10):
        for _ in range(cnt):
            nx, ny = self.rp()
            self.etty.append(ET(self, nx, ny))

    def alct(self):
        self.clr()
        for e in self.etty:
            cx, cy = self.clxy(e.x, e.y)
            self.cl[cx][cy].append(e)

    def clxy(self, x, y):
        return (
            int(clamp(x, 0, self.x-1) / self.cs),
            int(clamp(y, 0, self.y-1) / self.cs),
        )

    def cmpt_bsc(self):
        rpf = list()
        for ea in self.etty:
            rpp = list()
            for eb in self.etty:
                if eb is not ea:
                    rpp.append((eb, ea.dst(eb)))
            ec, dc =  min(rpp, key=lambda x: x[1])
            rpf.append((ea, ec, dc))
        return(rpf)


    def cmpt_adv(self):
        self.alct()
        rpf = list()
        for ea in self.etty:
            rpp = list()
            xmax, ymax = self.clxy(ea.x+ea.p, ea.y+ea.p)
            xmin, ymin = self.clxy(ea.x-ea.p, ea.y-ea.p)
            for cx in range(xmin, xmax+1):
                for cy in range(ymin, ymax+1):
                    for eb in self.cl[cx][cy]:
                        if eb is not ea:
                            rpp.append((eb, ea.dst(eb)))
            ec, dc =  min(rpp, key=lambda x: x[1])
            rpf.append((ea, ec, dc))
        return(rpf)

class ET():

    id_counter = itertools.count()

    def __init__(self, mp: MP, x, y):
        self.mp = mp
        self.x = clamp(x, 0, mp.x-1)
        self.y = clamp(y, 0, mp.y-1)
        self.p = 150
        self.name = f"ET-{next(ET.id_counter)}"

    def __repr__(self):
        return f"{self.name}({int(self.x)},{int(self.y)})"

    def dst(self, o):
        dx = o.x - self.x
        dy = o.y - self.y
        return math.sqrt(dx**2 + dy**2)





mp = MP(1024, 768, cs=128)
mp.ppl(350)


tBsc = 0
tAdv = 0
checked = 0
matched = 0

RUNS = 1000
for _run in range(RUNS):

    print(f"Run [{_run+1}/{RUNS}]")

    # Bsc
    ts = time.time()
    bsc = mp.cmpt_bsc()
    tBsc += (time.time() - ts)

    # Adv
    ts = time.time()
    adv = mp.cmpt_adv()
    tAdv += (time.time() - ts)

    # Check
    for eBsc, oBsc, dBsc in bsc:
        checked += 1
        for eAdv, oAdv, dAdv in adv:
            if eBsc is eAdv:
                if dBsc != dAdv:
                    # print("Mismatch {} : {} [{}] =/= {} [{}]".format(eBsc, oBsc, round(dBsc, 2), oAdv, round(dAdv, 2)))
                    pass
                else:
                    matched +=1
                break

print(f"Matched {matched}/{checked} ({round(100*matched/checked,2)}%)")
print(f"Bsc total: {round(tBsc, 2)}")
print(f"Adv total: {round(tAdv, 2)}")