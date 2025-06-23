import sys
import time
import psutil
import os


process = psutil.Process(os.getpid())
mem_before = process.memory_info().rss / (1024 * 1024)
start_processing_time = time.perf_counter()

# Parameters
number_nurses = int(sys.argv[1]) # Number of nurses
number_weeks = int(sys.argv[2]) # Number of weeks
encoding = sys.argv[3] if len(sys.argv) > 3 else "staircase_among"



