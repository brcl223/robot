from matplotlib import pyplot as plt
import numpy as np


# Use latex, and other font stuff
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": "Helvetica",
})



DATADIR="./data/validation/"
RUN=3
def load_data():
    taus = np.load(f"{DATADIR}/collected_t.run-{RUN:03d}.npy")
    qs = np.load(f"{DATADIR}/collected_q.run-{RUN:03d}.npy")
    tau_nn = np.load(f"{DATADIR}/collected_nn_t.run-{RUN:03d}.npy")
    e = np.load(f"{DATADIR}/collected_e.run-{RUN:03d}.npy")

    return qs, e, taus, tau_nn



def main():
    # Load data
    qs, e, taus, tau_nn = load_data()


    # Generate plots
    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3)

    # q dot data
    ax1.plot(qs, taus, label=r'$\tau$')
    ax1.plot(qs, tau_nn, label=r'$\tau_{nn}$')
    ax1.set_title(r'Configuration vs. Holding Torques')
    ax1.set_ylabel(r'Torque [$N\cdot m$] ($\tau$)')
    ax1.set_xlabel(r'Configuration [rad] ($q$)')
    ax1.legend()


    ax2.plot(qs, e)
    ax2.set_title('Configuration vs. Error')
    ax2.set_ylabel(r'Error [rad] ($e$)')
    ax2.set_xlabel(r'Configuration [rad] ($q$)')


    # ax3.plot(qs, label=r'$q$')
    ax3.plot(e, label=r'$e$')
    ax3.set_title('Error')
    ax3.set_ylabel('Distance [rad]')
    ax3.set_xlabel('Step')
    ax3.legend()

    fig.show()
    plt.show()



if __name__ == '__main__':
    main()
