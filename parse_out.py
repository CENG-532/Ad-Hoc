
hop1 = []
hop2 = []
hop3 = []
hop4 = []
f = open("timenodeA.txt", "r")
l = f.read().splitlines()
for line in l:
    _, hop, time = line.split(" ")
    if hop == "1":
        hop1.append(float(time))
    elif hop == "2":
        hop2.append(float(time))
    elif hop == "3":
        hop3.append(float(time))
    elif hop == "4":
        hop4.append(float(time))

print(hop1)
print(hop2)
print(hop3)
print(hop4)