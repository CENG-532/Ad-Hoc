
files_loss_5_bully = []
files_loss_10_bully = []
files_loss_15_bully = []

files_loss_5_aefa = ["aefa/timenodeA5.txt", "aefa/timenodeB5.txt", "aefa/timenodeC5.txt", "aefa/timenodeD5.txt", "aefa/timenodeE5.txt"]
files_loss_10_aefa = []
files_loss_15_aefa = []


def take_average(file_list, out_name):
    file_out = open(out_name, 'w')

    file_pointer_list = [open(file, 'r') for file in file_list]

    for line in file_pointer_list[0]:
        avg_value = float(line.split()[0])
        for i in range(1, len(file_list)):
            avg_value += float(file_pointer_list[i].readline().split()[0])

        file_out.write(str(avg_value/len(file_list)) + "\n")
        print(avg_value, avg_value/len(file_list))


if __name__ == "__main__":
    take_average(files_loss_5_aefa, "file_avg_test")
