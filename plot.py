import matplotlib.pyplot as plt
import numpy as np


def confidence_interval_calculation(data, exp_num):
    mean = []
    err = []
    for i in data:
        mean.append(np.mean(i))
        sd = np.std(i)
        err.append(1.960 * sd / np.sqrt(exp_num))
    return mean, err


def plot(rdt, sctp, exp_num, title, xlabel, fig_name, xtick_label):
    x_axis = np.arange(3)

    fig, ax = plt.subplots()
    rdt_means, rdt_errs = confidence_interval_calculation(rdt, exp_num)
    sctp_means, sctp_errs = confidence_interval_calculation(sctp, exp_num)
    plt.errorbar(x_axis, rdt_means, color='r', yerr=rdt_errs, label="RDT")
    plt.errorbar(x_axis, sctp_means, color='y', yerr=sctp_errs, label="SCTP")

    # print(np.sum(rdt,axis=1)/exp_num)
    print(rdt_means)

    plt.title(title)
    plt.legend(loc="upper left")
    plt.ylabel('file transfer time')
    plt.xlabel(xlabel)
    ax.set_xticks(x_axis)
    ax.set_xticklabels(xtick_label)
    fig.savefig(fig_name, dpi=fig.dpi)


def plot2(rdt, sctp, rdt_m, sctp_m, exp_num, title, xlabel, fig_name, xtick_label):
    x_axis = np.arange(3)
    width = 0.35

    fig, ax = plt.subplots()
    rdt_means, rdt_errs = confidence_interval_calculation(rdt, exp_num)
    sctp_means, sctp_errs = confidence_interval_calculation(sctp, exp_num)
    # rdt_means_m, rdt_errs_m = confidence_interval_calculation(rdt_m, exp_num)
    # sctp_means_m, sctp_errs_m = confidence_interval_calculation(sctp_m, exp_num)
    plt.errorbar(x_axis, rdt_means, color='r', yerr=rdt_errs)
    plt.errorbar(x_axis, sctp_means, color='y', yerr=sctp_errs, label="SCTP(no multi-homing)")
    # plt.errorbar(x_axis, rdt_means_m, color='b', yerr=rdt_errs_m, label="RDT(multi-homed)")
    # plt.errorbar(x_axis, sctp_means_m, color='g', yerr=sctp_errs_m, label="SCTP(multi-homed)")

    # print(np.sum(rdt,axis=1)/exp_num)
    # print(rdt_means)

    plt.title(title)

    plt.ylabel('election time(sec)')
    plt.xlabel(xlabel)
    ax.set_xticks(x_axis)
    ax.set_xticklabels(xtick_label)
    fig.savefig(fig_name, dpi=fig.dpi)


def plot_hop(rdt, exp_num, title, xlabel, fig_name, xtick_label):
    x_axis = np.arange(4)
    width = 0.35

    fig, ax = plt.subplots()
    rdt_means, rdt_errs = confidence_interval_calculation(rdt, exp_num)

    # rdt_means_m, rdt_errs_m = confidence_interval_calculation(rdt_m, exp_num)

    plt.errorbar(x_axis, rdt_means, color='r', yerr=rdt_errs, label="RDT(no multi-homing)")

    # plt.errorbar(x_axis, rdt_means_m, color='b', yerr=rdt_errs_m, label="RDT(multi-homed)")

    # print(np.sum(rdt,axis=1)/exp_num)
    print(rdt_means)

    plt.title(title)
    plt.legend(loc="upper left")
    plt.ylabel('file transfer time(sec)')
    plt.xlabel(xlabel)
    ax.set_xticks(x_axis)
    ax.set_xticklabels(xtick_label)
    fig.savefig(fig_name, dpi=fig.dpi)


def readFromFile(dir):
    data_dict = {}
    node_name = 'A'
    loss_array = ['5', '10', '15']
    node_number = 5
    for i in range(0, node_number):
        # for a node
        for loss in loss_array:
            f = open(dir + "/timenode" + node_name + str(loss) + ".txt", "r")
            l = f.read().splitlines()
            temp = []
            for line in l:
                temp.append(float(line))
            data_dict[node_name + str(loss)] = temp
        node_name = chr(ord(node_name) + 1)
    # for i in data_dict.keys():
    #     print(i, data_dict[i], len(data_dict[i]))

    return data_dict


# hop 2 node A 400 delay
hop_1_node_A = [0.001165, 0.001048, 0.00155, 0.00191, 0.002124, 0.001843, 0.001584, 0.002205, 0.001374, 0.002055,
                0.001766, 0.002079, 0.001137, 0.001841, 0.001566, 0.00214, 0.001413, 0.003348, 0.001608, 0.000986]

hop_2_node_A = [0.008728, 0.003906, 0.002521, 0.00351, 0.003066, 0.002753, 0.002278, 0.002693, 0.003246, 0.003118,
                0.002591, 0.002863, 0.00293, 0.002728, 0.002601, 0.004728, 0.003904, 0.003141, 0.002918, 0.001971]

hop_3_node_A = [0.008168, 0.002993, 0.002595, 0.004498, 0.00457, 0.00409, 0.004334, 0.004132, 0.004605, 0.003969,
                0.004063, 0.004414, 0.002539, 0.004419, 0.003435, 0.004497, 0.009397, 0.003561, 0.003836, 0.004509]

hop_4_node_A = [0.01084, 0.003801, 0.004921, 0.003788, 0.005821, 0.003765, 0.004707, 0.004841, 0.006831, 0.005182,
                0.005025, 0.005387, 0.00577, 0.003763, 0.004606, 0.004029, 0.004847, 0.004259, 0.006395, 0.004813]

node_A = [hop_1_node_A, hop_2_node_A, hop_3_node_A, hop_4_node_A]

# data
exp_num = 20

# without multihoming
rdt_lp_1 = [[0.971, 0.932, 0.879, 0.959, 1.047, 0.913, 0.817, 1.004, 0.946, 0.945],
            [1.449, 1.092, 1.430, 1.223, 1.530, 1.153, 1.211, 1.458, 1.149, 1.198],
            [1.692, 1.777, 1.730, 1.468, 1.710, 1.761, 1.654, 1.487, 2.250, 1.459]]
sctp_lp_1 = [[1.780, 1.315, 2.443, 1.518, 1.642, 1.721, 2.009, 1.728, 2.132, 1.920],
             [32.356, 229.730, 48.771, 49.351, 50.331, 56.498, 63.809, 56.979, 51.181, 68.281],
             [765.551, 680.555, 326.073, 759.586, 557.640, 504.696, 736.613, 317.778, 568.878, 605.467]]

rdt_lp_2 = [[1.027, 0.969, 0.834, 0.875, 0.872, 0.946, 0.957, 0.893, 0.890, 0.836],
            [1.413, 1.119, 1.213, 1.119, 1.084, 1.100, 1.365, 1.301, 1.109, 1.214, 1.194],
            [1.651, 2.267, 1.680, 1.350, 1.494, 1.524, 1.340, 1.432, 1.320, 1.546]]
sctp_lp_2 = [[1.891, 1.819, 1.283, 1.861, 1.749, 1.503, 1.940, 1.605, 1.261, 2.038],
             [42.875, 158.990, 41.078, 64.216, 57.268, 44.593, 44.356, 42.851, 54.310, 44.149],
             [200.867, 752.913, 555.207, 235.363, 615.579, 680.563, 476.840, 367.896, 603.276, 617.381]]

rdt_cp = [[0.930, 0.892, 0.831, 0.879, 0.889, 0.923, 0.923, 0.871, 0.969, 0.903],
          [1.305, 1.156, 1.237, 1.391, 1.074, 1.129, 1.424, 1.408, 1.223, 1.379],
          [2.670, 3.350, 2.341, 1.973, 2.878, 3.082, 2.143, 2.455, 3.055, 2.781]]
sctp_cp = [[2.124, 5.046, 2.166, 2.047, 1.650, 2.025, 1.633, 1.692, 1.995, 1.526],
           [35.456, 41.417, 50.857, 49.225, 49.341, 43.303, 48.093, 43.848, 60.275, 54.001],
           [2141.610, 2109.114, 2378.374, 2455.766, 2374.598, 2245.093, 2264.640, 2526.334, 2421.183, 2281.414]]

rdt_rp = [[0.899, 1.017, 0.979, 0.907, 0.937, 0.848, 1.069, 0.855, 0.882, 0.987],
          [1.016, 0.880, 0.889, 1.013, 0.878, 0.874, 0.969, 1.062, 1.024, 0.866],
          [0.800, 0.894, 0.959, 0.857, 0.950, 0.820, 0.886, 0.983, 0.816, 0.845]]
sctp_rp = [[0.852, 0.859, 0.856, 0.857, 0.996, 0.994, 1.003, 0.994, 0.993, 0.855],
           [2.425, 2.854, 2.138, 2.106, 2.129, 2.516, 2.190, 2.190, 2.479, 2.166],
           [5.454, 4.311, 4.848, 3.639, 4.833, 3.728, 3.684, 4.118, 4.419, 4.815]]

# plot2(rdt_lp_1, sctp_lp_1, rdt_lp_2, sctp_lp_2, exp_num, 'Packet Loss Percentage vs File Transfer Time',
#       'packet loss percentage', "exp_lp.png", ('0.1%', '5%', '10%'))
plot(rdt_lp_2, sctp_lp_2, exp_num, 'Experiment 2 Packet Loss Percentage vs File Transfer Time',
     'packet loss percentage', "exp2_lp.png", ('0.1%', '5%', '10%'))
# plot(rdt_cp, sctp_cp, exp_num, 'Corruption Percentage vs File Transfer Time', 'corruption percentage', "exp_cp.png",
#      ('0.1%', '5%', '20%'))
# plot(rdt_rp, sctp_rp, exp_num, 'Reordering Percentage vs File Transfer Time', 'reordering percentage', "exp_rp.png",
#      ('5%', '20%', '35%'))

# plot_hop(node_A, exp_num, "text1", "text2", "hop.png", ('0.1%', '5%', '10%'))
if __name__ == '__main__':
    # plot2(node_A, [], [], [], exp_num, 'Hop Count vs Data Transfer Time',
    #       'hop count', "hop.png", ('1', '2', '3', '4'))

    aefa_dict = readFromFile("aefa")
    bully_dict = readFromFile("bully")
    loss_array = [[bully_dict["A5"], bully_dict["A10"], bully_dict["A15"]],
                  [aefa_dict["A5"], aefa_dict["A10"], aefa_dict["A15"]]]
    print(loss_array[1])
    # plot2(loss_array[0], [], [], [], exp_num, 'Loss Percentage vs Election Time',
    #       'packet loss percentage', "bully_loss.png", ('5', '10', '15'))
    #
    # plot2(loss_array[1], [], [], [], exp_num, 'Loss Percentage vs Election Time',
    #       'packet loss percentage', "aefa_loss", ('5', '10', '15'))

    plot2(loss_array[0], loss_array[1], [], [], exp_num, 'Loss Percentage vs Election Time',
          'packet loss percentage', "bully_loss.png", ('5', '10', '15'))