import numpy as np
import asyncio
import moteus
import math
import collections
import os
import pathlib


DATADIR="./data/collection/"

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
    return max_seen + 1


pathlib.Path(DATADIR).mkdir(parents=False, exist_ok=True)
RUN=find_run_num()
print(f"Beginning run {RUN}...")
# import sys; sys.exit(0)
MAX_TORQUE = 0.15 # Units Nm
# MAX_TORQUE = 0.005 # Units Nm


# Units for Moteus GUI are in rotations
def sampler(samples, q_min=-2., q_max=2.):
    q_min = max(q_min, -20.)
    q_max = min(q_max, 20.)
    return np.linspace(q_min, q_max, samples, endpoint=True)


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


async def main():
    c = moteus.Controller()

    # Clear error if present
    await c.set_stop()
    q = 0.
    q_dot = 0.
    qd_dot = 0.
    torque = 0

    collected_q = []
    collected_t = []

    POINTS_TO_COLLECT = 250

    # points = sampler(POINTS_TO_COLLECT, q_min=-4., q_max=4.)
    # Go from 0 -> END, END -> 0, 0 -> -END, -END -> 0
    END = 12
    points1 = sampler(POINTS_TO_COLLECT, q_min=0., q_max=END)
    points2 = np.copy(points1)[::-1]
    points3 = sampler(POINTS_TO_COLLECT, q_min=-END, q_max=0.)[::-1]
    points4 = np.copy(points3)[::-1]
    points = np.concatenate((points1, points2, points3, points4))

    for point in points:
        reset = True
        qd = point

        print(f"Moving to desired qd: {qd}")

        while not is_stopped(q_dot, reset=reset):
            reset = False
            state = await c.set_position(position=math.nan,
                                     kp_scale=0, kd_scale=0,
                                     feedforward_torque=torque, maximum_torque=MAX_TORQUE,
                                     query=True)
            # state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, query=True)

            # print(state)

            q = state.values[moteus.Register.POSITION]
            q_dot = state.values[moteus.Register.VELOCITY]

            torque = pid_control(q, q_dot, qd, qd_dot, Ki = 0, Kp = 0.2, Kd = 0.03)
            # print(f"\nCommanded Torque: {torque}")
            # print(f"Read torque: {state.values[moteus.Register.TORQUE]}\n")

            await asyncio.sleep(0.02)

        print(f"Stopped!\nq: {q}\nTorque: {torque}\n")
        collected_q.append(q)
        collected_t.append(torque)

    print("Saving collected data...")
    np.save(f"./data/collected_q.run-{RUN:03d}.npy", collected_q)
    np.save(f"./data/collected_t.run-{RUN:03d}.npy", collected_t)
    print("Data saved!")


    # while True:
    #     # Be VERY careful with the commanded feedforward_torque
    #     # kp_scale = kd_scale = 0 => pure feedforward_torque controller
    #     # state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, feedforward_torque=0.001, query=True)
    #     state = await c.set_position(position=math.nan,
    #                                  kp_scale=0, kd_scale=0,
    #                                  feedforward_torque=torque, maximum_torque=MAX_TORQUE,
    #                                  query=True)
    #     # state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, query=True)

    #     print(state)

    #     q_cur = state.values[moteus.Register.POSITION]
    #     q_dot_cur = state.values[moteus.Register.VELOCITY]
    #     q = discrete_lowpass(q_cur, q)
    #     q_dot = discrete_lowpass(q_dot_cur, q_dot)
    #     qd = 2.0
    #     qd_dot = 0.

    #     torque = pid_control(q, q_dot, qd, qd_dot, Ki = 0, Kp = 0.18, Kd = 0.025)
    #     print(f"\nCommanded Torque: {torque}")
    #     print(f"Read torque: {state.values[moteus.Register.TORQUE]}\n")

    #     await asyncio.sleep(0.02)


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
