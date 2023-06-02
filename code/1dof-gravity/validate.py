import numpy as np
import torch
import torch.nn as nn
import asyncio
import moteus
import math
import collections
import os
import pathlib



# Number motor rotations per one link rotation
MOTOR_LINK_RATIO = 6


def load_nn(model_path, hidden=100):
    INPUTS = 1
    OUTPUTS = INPUTS
    net = nn.Sequential(nn.Linear(INPUTS, hidden),
                        nn.ReLU(),
                        nn.Linear(hidden, hidden),
                        nn.ReLU(),
                        nn.Linear(hidden, OUTPUTS)).double()
    checkpoint = torch.load(model_path)
    net.load_state_dict(checkpoint['model_state_dict'])
    net.eval()
    return net




DATADIR = "./data/validation/"
#123456789abc
#cba987654321
#".run-123.npy"
def find_run_num():
    global DATADIR
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
RUN = find_run_num() + 1
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
    print("Loading network...")
    model_path = "./models/test-test-3_nodes-model_4.chkpnt"
    holding_torques = load_nn(model_path)
    print("Network loaded!\n\n")

    c = moteus.Controller()

    # Clear error if present
    await c.set_stop()
    q = 0.
    q_dot = 0.
    qd_dot = 0.
    torque = 0

    collected_q = []
    collected_t = []
    collected_nn_t = []
    collected_e = []

    POINTS_TO_COLLECT = 20

    # points = sampler(POINTS_TO_COLLECT, q_min=-4., q_max=4.)
    # Go from 0 -> END, END -> 0, 0 -> -END, -END -> 0
    # Units: Rotations of motor (link is 1 rotation / 6 rotations motor)
    END = 12
    points1 = sampler(POINTS_TO_COLLECT, q_min=0., q_max=END)
    points2 = np.copy(points1)[::-1]
    points3 = sampler(POINTS_TO_COLLECT, q_min=-END, q_max=0.)[::-1]
    points4 = np.copy(points3)[::-1]
    points = np.concatenate((points1, points2, points3, points4))

    print("Beginning data collection...")
    for point in points:
        reset = True
        qd = point
        qd_nn_input = qd % MOTOR_LINK_RATIO
        nn_torque = holding_torques(torch.tensor([qd_nn_input])).detach().numpy()[0]

        print(f"Moving to desired qd: {qd}")
        print(f"Input qd: {qd_nn_input}")
        print(f"Predicted NN Holding Torque: {nn_torque}")

        while not is_stopped(q_dot, reset=reset):
            reset = False
            torque += nn_torque
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

        error = qd - q
        print(f"Stopped!\nq: {q}\nError: {error}\nPD Torque: {torque}\nTotal Torque: {torque + nn_torque}")
        collected_q.append(q)
        collected_t.append(torque)
        collected_nn_t.append(nn_torque)
        collected_e.append(error)

    print("Saving collected data...")
    np.save(f"{DATADIR}/collected_q.run-{RUN:03d}.npy", collected_q)
    np.save(f"{DATADIR}/collected_t.run-{RUN:03d}.npy", collected_t)
    np.save(f"{DATADIR}/collected_nn_t.run-{RUN:03d}.npy", collected_nn_t)
    np.save(f"{DATADIR}/collected_e.run-{RUN:03d}.npy", collected_e)
    print("Data saved!")



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
