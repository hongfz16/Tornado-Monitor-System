import time
from threading import Thread
threads = []

def work(k):
	time.sleep(2)
	# print(k)
	return k

for i in range(10):
	t = Thread(target=work, args=(i,))
	threads.append(t)
# Start all threads
for x in threads:
    x.start()
# Wait for all of them to finish
for x in threads:
    x.join()
print("main")