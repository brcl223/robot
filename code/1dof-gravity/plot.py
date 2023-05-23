from matplotlib import pyplot as plt
import numpy as np


# Use latex, and other font stuff
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": "Helvetica",
})



def load_data():
    q_d_f = np.load("data/q_dot_filtered_data.npy")
    q_d_r = np.load("data/q_dot_raw_data.npy")
    q_f = np.load("data/q_filtered_data.npy")
    q_r = np.load("data/q_raw_data.npy")
    t = np.load("data/torque_data.npy")

    return q_d_f, q_d_r, q_f, q_r, t



def main():
    # Load data
    q_df, q_dr, q_f, q_r, torque = load_data()


    # Generate plots
    fig, (ax_qd, ax_q, ax_t) = plt.subplots(nrows=3)

    # q dot data
    ax_qd.plot(q_df, label=r'$\dot q_f$')
    ax_qd.plot(q_dr, label=r'$\dot q_r$')
    ax_qd.legend()
    ax_qd.set_title(r'Velocity Filtered ($f$) vs. Raw ($r$)')
    ax_qd.set_ylabel('Revolution / s')

    # q data
    ax_q.plot(q_f, label=r'$q_f$')
    ax_q.plot(q_r, label=r'$q_r$')
    ax_q.legend()
    ax_q.set_title(r'Position Filtered ($f$) vs. Raw ($r$)')
    ax_q.set_ylabel('Revolution')

    # Torque data
    ax_t.plot(torque, label=r'$\tau$')
    ax_t.legend()
    ax_t.set_title(r'Commanded Torque')
    ax_t.set_ylabel(r'$N\cdot m$')


    fig.show()
    plt.show()



if __name__ == '__main__':
    main()
