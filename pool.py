from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import cpu_count

TPE = ThreadPoolExecutor(max_workers=cpu_count())
