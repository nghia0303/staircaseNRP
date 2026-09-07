#!/bin/bash

# ==== Đường dẫn ====
VENV_3_12_PATH="/home/nghia/Desktop/Crew/staircase/.venv/bin/activate"
VENV_3_8_PATH="/home/nghia/Desktop/Crew/staircase/.venv1/bin/activate"
SRC_PATH="/home/nghia/Desktop/Staircase/staircaseNRP"

SCRIPT1="${SRC_PATH}/src/test/run_nurse_rostering.py"
SCRIPT2="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/NRP_gurobi.py"

CPLEX_MP_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/MIP/main.py"
#CPLEX_CP_PATH="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/model/NRP.mod"
CPLEX_CP_PATH="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/model/nrp.py"
HADDOCK_CP_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/sequenceNurse"
HADDOCK_CP_SEQ_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/sequenceNurseNew"
 #-w32 -m0 -n30 -d84
PICAT_PATH="${SRC_PATH}/Compare_NRP/Picat/model.pi"

DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_${DATE_STR}.csv"
SHORTEN_RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_short_${DATE_STR}.csv"


mkdir -p "${SRC_PATH}/Compare_NRP/CSV/"

RESULT_DIR="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/Results"
TIMEOUT=600 # Thời gian chạy tối đa cho mỗi lệnh (giây)

# ==== Thông số chạy ====
NURSE_LIST=(30 40 50 60 70 80 100 120)
#WEEK_LIST=(4)
DAY_LIST=(84 112 140 168)

#NURSE_LIST=(120)
#WEEK_LIST=(24)

# ==== Hàm giải phóng bộ nhớ hệ thống (tùy chọn – cần sudo) ====
cleanup_memory() {
  echo "Cleaning memory cache..."
  sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
}

sudo -v  # Kiểm tra quyền sudo

# ==== Kích hoạt môi trường ảo ====
# shellcheck disable=SC1090
source "$VENV_3_12_PATH"

# Tạo file CSV nếu chưa có
if [ ! -f "$RESULT_CSV" ]; then
  echo "Creating result CSV file..."
  echo "nurses,days,model,encoding,clauses,vars,encoding_time,solving_time,total_time,validation" > "$RESULT_CSV"
fi

# Tạo file CSV rút gọn nếu chưa có
if [ ! -f "$SHORTEN_RESULT_CSV" ]; then
  echo "Creating shortened result CSV file..."
  echo "model,nurses,week,total_time(ms),peak_ram(kb),solns" > "$SHORTEN_RESULT_CSV"
fi

# Tạo thư mục kết quả nếu chưa có
mkdir -p "$RESULT_DIR"
mkdir -p "tmp/solver_output/sat"
mkdir -p "tmp/solver_output/gurobi"
mkdir -p "tmp/solver_output/cplex_mp"
mkdir -p "tmp/solver_output/cplex_cp"


# ==== Chạy các tổ hợp ====
for NURSES in "${NURSE_LIST[@]}"; do
  for DAYS in "${DAY_LIST[@]}"; do
    echo "${NURSES} nurses, ${DAYS} days"
    cleanup_memory
    echo "============================================"
    # Chạy script SAT
    echo "[SAT-Staircase_among] Running..."
    source "$VENV_3_12_PATH"
    mem_file=$(mktemp)
    method="staircase_among"
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$SCRIPT1" "$NURSES" "$DAYS" "$method" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')
    echo "Total time for SAT: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "staircase_among,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"

    cleanup_memory
    echo "============================================"
    # Chạy script SAT
    echo "[SAT-Staircase_at_least] Running..."
    source "$VENV_3_12_PATH"
    mem_file=$(mktemp)
    method="staircase_at_least"
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$SCRIPT1" "$NURSES" "$DAYS" "$method" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for SAT: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "staircase_at_least,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"


    cleanup_memory
    echo "============================================"
    # Chạy script SAT
    echo "[SAT-Staircase_direct] Running..."
    source "$VENV_3_12_PATH"
    mem_file=$(mktemp)
    method="staircase_direct"
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$SCRIPT1" "$NURSES" "$DAYS" "$method" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for SAT: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "staircase_direct,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"
  done
done
