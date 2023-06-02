from matplotlib import pyplot as plt
import numpy as np
import os


# Use latex, and other font stuff
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": "Helvetica",
})

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


DATADIR="./data/validation/"

# Switch to specific run if wanting different data
# Else plots most recent data
RUN = find_run_num()

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
    fig, ((ax1, ax3), (ax2, ax4)) = plt.subplots(nrows=2, ncols=2)

    # q dot data
    ax1.plot(qs, taus, label=r'$\tau_{pd}$')
    ax1.plot(qs, tau_nn, label=r'$\tau_{nn}$')
    ax1.set_title(r'Configuration vs. Holding Torques')
    ax1.set_ylabel(r'Torque [$N\cdot m$] ($\tau$)')
    ax1.set_xlabel(r'Motor Configuration [rot] ($q$)')
    ax1.legend()

    ax2.plot(qs, taus + tau_nn, label=r'$\tau_{pd} + \tau_{nn}$')
    ax2.set_title(r'Configuration vs. Combined Holding Torques')
    ax2.set_ylabel(r'Torque [$N\cdot m$] ($\tau$)')
    ax2.set_xlabel(r'Motor Configuration [rot] ($q$)')
    ax2.legend()

    ax1.sharex(ax2)


    ax3.plot(qs, e)
    ax3.set_title('Configuration vs. Error')
    ax3.set_ylabel(r'Error [rot] ($e$)')
    ax3.set_xlabel(r'Motor Configuration [rot] ($q$)')


    # ax3.plot(qs, label=r'$q$')
    ax4.plot(e)
    ax4.set_title('Error')
    ax4.set_ylabel('Distance [rot]')
    ax4.set_xlabel('Step')

    fig.tight_layout()
    fig.show()
    plt.show()



if __name__ == '__main__':
    main()
