#!/usr/bin/env python3
"""Synthesize original short promo sounds (clicks, pops, whooshes, impacts, chimes). No samples or third-party recordings used.
Use only for roles where no fitting recorded sound (buckle, zipper, metal, engine) is available."""
import argparse
import array
import math
from pathlib import Path
import random
import sys
import wave

RATE = 48000

def sound(kind):
    duration = {'click':.16,'click-alt':.12,'pop':.22,'toggle':.25,'typing':.65,'ding-dong':1.15,'success':.85,'error':.7,'resolve':1.55,'whoosh':.38,'sweep':.65,'impact':.9}[kind]
    samples = [0.0] * round(duration * RATE)
    def bell(at, frequency, length, level):
        offset = round(at * RATE)
        for i in range(min(round(length * RATE), len(samples)-offset)):
            t = i / RATE
            env = (1-math.exp(-t/0.004)) * math.exp(-t/(length/5)) * min(1,(length-t)/.025)
            partial = math.sin(math.tau*frequency*t) + .16*math.sin(math.tau*frequency*2*t)*math.exp(-t*12)
            samples[offset+i] += level*env*partial
    if kind == 'click':
        bell(0, 740, .14, .15)
    elif kind == 'click-alt':
        bell(0,590,.10,.14)
    elif kind == 'pop':
        for i in range(len(samples)):
            t=i/RATE
            phase=math.tau*(240*t+480*.022*(1-math.exp(-t/.022)))
            samples[i]=.22*math.sin(phase)*(1-math.exp(-t/.002))*math.exp(-t*28)
    elif kind == 'toggle':
        bell(0,600,.11,.13);bell(.07,920,.15,.16)
    elif kind == 'typing':
        rng=random.Random(42)
        for j,at in enumerate([0,.085,.18,.245,.39,.49]):
            bell(at,650+90*(j%3),.06,.07)
            pos=round(at*RATE)
            for i in range(round(.022*RATE)):
                if pos+i<len(samples):samples[pos+i]+=.04*rng.uniform(-1,1)*math.sin(math.pi*i/(.022*RATE))*math.exp(-i/RATE*120)
    elif kind in ['success','error']:
        notes=[659.25,783.99,1046.5] if kind=='success' else [440,349.23]
        for i,hz in enumerate(notes):bell(i*.10,hz,.55,.15)
    elif kind == 'ding-dong':
        bell(0, 1046.5, .7, .22)
        bell(.19, 783.99, .92, .23)
    elif kind == 'resolve':
        for at, freq in [(0,523.25),(.11,659.25),(.22,783.99)]: bell(at,freq,1.2,.14)
    elif kind == 'impact':
        # Low thump for a product landing on its mark: pitch-dropping sine plus a short noise transient.
        rng=random.Random(2026)
        for i in range(len(samples)):
            t=i/RATE
            phase=math.tau*(48*t+90*.06*(1-math.exp(-t/.06)))
            samples[i]=.5*math.sin(phase)*(1-math.exp(-t/.003))*math.exp(-t*5.5)
            if t<.03:samples[i]+=.08*rng.uniform(-1,1)*math.exp(-t*160)
    else:
        rng=random.Random(7418); low=0
        for i in range(len(samples)):
            t=i/RATE; low=.87*low+.13*rng.uniform(-1,1)
            samples[i]=low*.24*math.sin(math.pi*t/duration)**2
            if kind=='sweep':samples[i]+=.035*math.sin(math.tau*(260*t+360*t*t))*math.sin(math.pi*t/duration)**2
    pcm=array.array('h', (round(max(-.95,min(.95,x))*32767) for x in samples))
    if sys.byteorder!='little':pcm.byteswap()
    return pcm

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    names=['click','click-alt','pop','toggle','typing','ding-dong','success','error','resolve','whoosh','sweep','impact']
    if any((args.output/(name+'.wav')).exists() for name in names):
        p.error('Sound files already exist; use a new output directory to avoid replacing custom assets.')
    args.output.mkdir(parents=True,exist_ok=True)
    for name in names:
        with wave.open(str(args.output/(name+'.wav')),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes(sound(name).tobytes())
    (args.output/'SOURCE.txt').write_text('Original procedural promo sounds made with scripts/make_sfx.py. No samples, external recordings, or reference-video audio used. Replace these sounds when another sound better suits the product.\n')
    print(f'Generated {len(names)} original sound variants at 48 kHz. Audition in the final mix.')
if __name__=='__main__':main()
