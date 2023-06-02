import numpy as np
import asyncio
import moteus
import math
import collections
import os
import pathlib
import time


DATADIR="./data/collection/dynamic/"

#123456789abc
#cba987654321
# ".run-123.npy"
def find_run_num():
    max_seen = 0
    for filename in os.scandir(DATADIR):
        if filename.is_file and ".run-" in filename.name:
            run_str_start = filename.name.find('.run-') + len('.run-')
            # print(f"rss: {run_str_start}")
            # print(f"Fname len: {len(filename.name)}")
            # print(f"Filename: {filename.name}")
            # print(f"Selected substring: {filename.name[run_str_start:run_str_start+3]}")
            max_seen = max(max_seen, int(filename.name[run_str_start:run_str_start+3]))
    return max_seen


pathlib.Path(DATADIR).mkdir(parents=False, exist_ok=True)
RUN=find_run_num() + 1
print(f"Beginning run {RUN}...")
# import sys; sys.exit(0)
MAX_TORQUE = 0.15 # Units Nm
# MAX_TORQUE = 0.005 # Units Nm


# Units for Moteus GUI are in rotations
def sampler(samples, q_min=-2., q_max=2.):
    q_min = max(q_min, -20.)
    q_max = min(q_max, 20.)
    return np.linspace(q_min, q_max, samples, endpoint=True)


def gen_next_point(qd_0, qd_dot, dt):
    return qd_0 + qd_dot * dt


VEL_SAMPLES = 50
# VEL_THRESH = 1e-3
VEL_THRESH = 5e-4
CIRCLEBUF = collections.deque(maxlen=VEL_SAMPLES)
def is_stopped(qvel_cur, reset:bool = False):
    global CIRCLEBUF, VEL_SAMPLES

    if reset:
        CIRCLEBUF.clear()

    CIRCLEBUF.append(qvel_cur)
    if len(CIRCLEBUF) < VEL_SAMPLES:
        return False

    avg_vel = sum(CIRCLEBUF) / len(CIRCLEBUF)
    if avg_vel < VEL_THRESH:
        print(f"Stopped at q_dot={avg_vel}")
        return True

    return False



sum_e = 0.
def pid_control(q, q_dot, qd, qd_dot, Kp = 0.01, Kd = 0.008, Ki = 0.001):
    global sum_e
    e = qd - q
    e_dot = qd_dot - q_dot
    sum_e += e
    return Kp * e + Kd * e_dot + Ki * sum_e



# Really no need for this since it appears Moteus applies low-pass filter on
# joint configuration / velocity readings. But keeping here because it's already
# implemented and may end up being useful.
def discrete_lowpass(x, y_prev, alpha=0.5):
    return alpha * x + (1 - alpha) * y_prev


ctr = 0
def after_num_ms(t_now, t_start, ms, reset=False):
    global ctr
    if reset: ctr = 0

    dt_ms = (t_now - t_start) * 1000
    if (ms + ctr * ms) < dt_ms:
        ctr += 1
        return True
    else:
        return False


async def main():
    c = moteus.Controller()

    # Clear error if present
    await c.set_stop()
    q = 0.
    q_dot = 0.
    qd_dot = 0.1 # Want constant velocity
    torque = torque_filtered = 0

    collected_q = []
    collected_q_dot = []
    collected_t = []
    collected_t_filtered = []
    collected_freq = []

    # Get initial reading
    state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, query=True)
    qd_0 = state.values[moteus.Register.POSITION]

    # Units: seconds
    COLLECTION_TIME = 3
    t_start = t_prev = time.time()


    # Initial guess of dt
    # Seems to be a decent ballpark figure
    dt = 1./300
    while (t_prev - t_start) < COLLECTION_TIME:
        t_now = time.time()
        dt = discrete_lowpass(t_now - t_prev, dt, alpha=0.6)
        qd = gen_next_point(qd_0, qd_dot, dt)

        state = await c.set_position(position=math.nan,
                                     kp_scale=0, kd_scale=0,
                                     feedforward_torque=torque_filtered, maximum_torque=MAX_TORQUE,
                                     query=True)
        # state = await c.set_position(position=math.nan,
        #                              kp_scale=0, kd_scale=0,
        #                              feedforward_torque=0, maximum_torque=MAX_TORQUE,
        #                              query=True)

        q = state.values[moteus.Register.POSITION]
        q_dot = state.values[moteus.Register.VELOCITY]

        torque = pid_control(q, q_dot, qd, qd_dot, Ki=0, Kp=0.3, Kd=0.05)
        torque_filtered = discrete_lowpass(torque, torque_filtered, alpha=0.99)

        collected_q.append(q)
        collected_q_dot.append(q_dot)
        collected_t.append(torque)
        collected_t_filtered.append(torque_filtered)
        collected_freq.append(1/dt)

        if after_num_ms(t_now, t_start, 500):
            print("########################################")
            print(f"Time [s]: {t_now - t_start}")
            print(f"Torque [Nm]: {torque}")
            print(f"Position [rot]: {q}")
            print(f"Desired Position [rot]: {qd}")
            print(f"Velocity [rot/s]: {q_dot}")
            print(f"Desired Velocity [rot/s]: {qd_dot}")
            print("########################################\n\n\n")

        t_prev = t_now
        qd_0 = qd

        await asyncio.sleep(0.005)


    print("Saving collected data...")
    np.save(f"{DATADIR}/collected_q.run-{RUN:03d}.npy", collected_q)
    np.save(f"{DATADIR}/collected_q_dot.run-{RUN:03d}.npy", collected_q_dot)
    np.save(f"{DATADIR}/collected_t.run-{RUN:03d}.npy", collected_t)
    np.save(f"{DATADIR}/collected_t_filtered.run-{RUN:03d}.npy", collected_t_filtered)
    print("Data saved!")

    collected_freq = collected_freq[10:]
    avg = lambda l : sum(l) / len(l)
    print(f"Average Frequency: {avg(collected_freq)}\nMax: {max(collected_freq)}\nMin: {min(collected_freq)}")

    import matplotlib.pyplot as plt
    plt.plot(collected_freq)
    plt.show()


async def disable_motor():
    c = moteus.Controller()
    await c.set_stop()


if __name__ == '__main__':
    # This part is needed due to the fact that the controller
    # object is shared on each async thread. Thus this ensures
    # the object is run on the same thread and avoids an exception?
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Received kill command")
    finally:
        print("Disable motors...")
        loop.run_until_complete(disable_motor())
        print("Disabled!")
