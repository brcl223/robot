from matplotlib import pyplot as plt
import numpy as np


# Use latex, and other font stuff
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": "Helvetica",
})



def load_data():
    taus = np.load("./data/collected_t.run-002.npy")
    qs = np.load("./data/collected_q.run-002.npy")

    return qs, taus



def main():
    # Load data
    qs, taus = load_data()


    # Generate plots
    fig, ax = plt.subplots()

    # q dot data
    ax.plot(qs, taus)
    ax.set_title(r'Configuration vs. Holding Torques')
    ax.set_ylabel(r'Torque [$N\cdot m$] ($\tau$)')
    ax.set_xlabel(r'Configuration [rad] ($q$)')

    fig.show()
    plt.show()



if __name__ == '__main__':
    main()
