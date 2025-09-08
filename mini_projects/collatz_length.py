import time

start_time = time.time()
max_steps = 0
max_steps_num = 0

def collatz_length(n):
    global max_steps, max_steps_num
    steps = 0
    num = n
    while n != 1:
        if not n%2:
            n //= 2
        else:
            n = (n*3)+1
        steps += 1
    if steps > max_steps:
        max_steps = steps
        max_steps_num = num


for i in range(1, 10_000_001):
    collatz_length(i)

end_time = time.time()
all_time = end_time - start_time

print(max_steps, max_steps_num, all_time)