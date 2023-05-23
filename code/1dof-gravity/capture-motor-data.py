import numpy as np
import asyncio
import moteus
import math
import time


BUFSIZE = 1000
q_raw_data = np.zeros(BUFSIZE)
q_filtered_data = np.zeros(BUFSIZE)
q_dot_raw_data = np.zeros(BUFSIZE)
q_dot_filtered_data = np.zeros(BUFSIZE)
torque_data = np.zeros(BUFSIZE)

# Units for Moteus GUI are in rotations
def sampler(samples, q_min, q_max):
    q_min = max(q_min, 0.)
    q_max = min(q_max, 1.)
    return np.linspace(q_min, q_max, samples, endpoint=False)


sum_e = 0.
def pid_control(q, q_dot, qd, qd_dot, Kp = 0.008, Kd = 0.008, Ki = 0.0005):
    global sum_e
    e = qd - q
    e_dot = qd_dot - q_dot
    sum_e += e
    print(f"sum_e: {sum_e}")
    return Kp * e + Kd * e_dot + Ki * sum_e



def discrete_lowpass(x, y_prev, alpha=0.5):
    return alpha * x + (1 - alpha) * y_prev


async def main():
    c = moteus.Controller()

    # Clear error if present
    await c.set_stop()
    q = 0.
    q_dot = 0.
    torque = 0.

    # while True:
    for i in range(BUFSIZE):
        # Be VERY careful with the commanded feedforward_torque
        # kp_scale = kd_scale = 0 => pure feedforward_torque controller
        # state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, feedforward_torque=0.001, query=True)
        state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, feedforward_torque=torque, query=True)
        # state = await c.set_position(position=math.nan, kp_scale=0, kd_scale=0, query=True)

        print(state)

        q_cur = state.values[moteus.Register.POSITION]
        q_dot_cur = state.values[moteus.Register.VELOCITY]
        q = discrete_lowpass(q_cur, q)
        q_dot = discrete_lowpass(q_dot_cur, q_dot)
        qd = 1.0
        qd_dot = 0.

        q_raw_data[i] = q_cur
        q_filtered_data[i] = q
        q_dot_raw_data[i] = q_dot_cur
        q_dot_filtered_data[i] = q_dot

        torque = pid_control(q, q_dot, qd, qd_dot)
        print(f"\nCommanded Torque: {torque}\n")

        torque_data[i] = torque

        # print(f"Values: {state.values}")
        # print(f"Position: {state.values[moteus.Register.POSITION]}")
        # print("\n")

        await asyncio.sleep(0.02)


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

    np.save("q_raw_data.npy", q_raw_data)
    np.save("q_filtered_data.npy", q_filtered_data)
    np.save("q_dot_raw_data.npy", q_dot_raw_data)
    np.save("q_dot_filtered_data.npy", q_dot_filtered_data)
    np.save("torque_data.npy", torque_data)
