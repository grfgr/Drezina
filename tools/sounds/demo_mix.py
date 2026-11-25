import subprocess, numpy as np, random, math, sys
SR=44100; snd=sys.argv[1]
def load(n):
    raw=subprocess.run(["ffmpeg","-loglevel","error","-i",f"{snd}/{n}.ogg","-f","f32le","-ac","1","-ar",str(SR),"-"],capture_output=True).stdout
    return np.frombuffer(raw,dtype=np.float32).copy()
roll=load("roll_loop"); brake=load("brake_loop")
clacks=[load(f"clack_{i}") for i in (1,2,3)]; creaks=[load(f"creak_{i}") for i in (1,2,3,4)]; knocks=[load(f"knock_{i}") for i in (1,2)]
T=16.0; N=int(T*SR); out=np.zeros(N+SR)
def add(x,t,g=1.0):
    i=int(t*SR); out[i:i+len(x)]+=x[:len(out)-i]*g
random.seed(3); dt=1/200; speed=0; lever=0; prevc=1; joint=8; second=-1; rc=3
vol_env=np.zeros(N); brake_env=np.zeros(N)
t=0
while t<T:
    pumping = t<7; braking = t>11.5
    acc=-0.25 + (1.3 if pumping else 0) - (4.0 if braking else 0)
    speed=max(0,min(9,speed+acc*dt))
    rate=speed*1.1
    if pumping and rate<2.5: rate=2.5
    lever+=rate*dt; c=math.cos(lever)
    if rate>0.5 and (c>=0)!=(prevc>=0):
        if random.random()<0.75: add(random.choice(creaks),t,0.6)
        if pumping and random.random()<0.35: add(random.choice(knocks),t,0.5)
    prevc=c
    if speed>0.8:
        joint+=speed*dt
        if joint>=12.5: joint-=12.5; add(random.choice(clacks),t,0.8); second=1.24/speed
    if second>=0:
        second-=dt
        if second<0: add(random.choice(clacks),t,0.75)
    if speed>1 and not pumping:
        rc-=dt
        if rc<=0: rc=random.uniform(2.5,7); add(random.choice(creaks),t,0.5)
    i0=int(t*SR); i1=int((t+dt)*SR)
    vol_env[i0:i1]= (min(max(speed/8,0.15),1) if speed>0.3 else 0)
    brake_env[i0:i1]= 1 if (braking and speed>0.3) else 0
    t+=dt
k=int(0.3*SR); ker=np.ones(k)/k
vol_env=np.convolve(vol_env,ker,'same'); brake_env=np.convolve(brake_env,np.ones(k//3)/(k//3),'same')
out[:N]+=np.resize(roll,N)*vol_env*0.55 + np.resize(brake,N)*brake_env*0.5
out=out/np.max(np.abs(out))*0.9
pcm=(out*32767).astype(np.int16).tobytes()
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","s16le","-ar",str(SR),"-ac","1","-i","-","-c:a","libmp3lame","-q:a","3","drezina_ride_demo.mp3"],input=pcm,check=True)
print("ok")
