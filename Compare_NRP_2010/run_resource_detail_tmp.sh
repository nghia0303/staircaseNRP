#!/bin/bash

# ==== Đường dẫn ====
VENV_3_12_PATH="/home/nghia/Desktop/Crew/staircase/venv/bin/activate"
VENV_3_8_PATH="/home/nghia/Desktop/Crew/staircase/venv4/bin/activate"

SRC_PATH="/home/nghia/Desktop/NRP_nghia"

AMONG_NURSE_SCRIPT="/home/nghia/Desktop/NRP_nghia/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/amongNurse"
STAIRCASE_PATH="/home/nghia/Desktop/NRP_nghia/src/test/NRP_2010.py"
CPLEX_CP_PATH="/home/nghia/Desktop/NRP_nghia/Compare_NRP_2010/CPLEX/CP/cp_model.py"
CPLEX_MP_PATH="/home/nghia/Desktop/NRP_nghia/Compare_NRP_2010/CPLEX/MP/mp_model.py"
GUROBI_PATH="/home/nghia/Desktop/NRP_nghia/Compare_NRP_2010/Gurobi/gurobi_model.py"

DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP_2010/CSV/result_${DATE_STR}.csv"
mkdir -p "${SRC_PATH}/Compare_NRP_2010/CSV/"

cleanup_memory() {
  echo "Cleaning memory cache..."
  sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
}


# Write header to CSV file
echo "method,width,mode,C,H,totalTime,timeToFirstSol,Sols" > "$RESULT_CSV"

sudo -v

chmod +x "$AMONG_NURSE_SCRIPT"



W_LIST=(1)
M_LIST=(0)
C_LIST=(3)
H_LIST=(40)
R_LIST=(1)
I_LIST=(1)


#CMD="$AMONG_NURSE_SCRIPT -w64 -m1 -r5 -i10 -c$1 -h$40 -n0 -na1 -d2 -ca1 -a1 -e1 -p0 -t3 -maxP0 -minP0 -wP0 -j1"
source "$VENV_3_12_PATH"
CMD="python3 "$STAIRCASE_PATH" 40 1 "staircase" "g421""

#CMD="python3 "$GUROBI_PATH" 50 3"


#source "$VENV_3_8_PATH"
#CMD="python3 $CPLEX_MP_PATH 80 3"
# Chạy tiến trình trong nền
$CMD &
pid=$!

# Tạo file log
LOG_FILE="usage_log.txt"
> "$LOG_FILE"

# Theo dõi RAM và số thread cho đến khi tiến trình kết thúc
while kill -0 "$pid" 2> /dev/null; do
    ps -p "$pid" -o rss=,nlwp= >> "$LOG_FILE"
    sleep 0.1
done

# Tính peak RAM (KB) và số thread tối đa
peak_ram=$(awk '{if($1>max) max=$1} END{print max}' "$LOG_FILE")
max_threads=$(awk '{if($2>max) max=$2} END{print max}' "$LOG_FILE")

echo "Peak RAM usage: ${peak_ram} KB"
echo "Max thread count: ${max_threads}"