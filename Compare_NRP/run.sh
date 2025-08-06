#!/bin/bash

# ==== Đường dẫn ====
VENV_3_12_PATH="/home/nghia/Desktop/Crew/staircase/venv/bin/activate"
VENV_3_8_PATH="/home/nghia/Desktop/Crew/staircase/venv4/bin/activate"
SRC_PATH="/home/nghia/Desktop/NRP_nghia"

SCRIPT1="${SRC_PATH}/src/test/run_nurse_rostering.py"
SCRIPT2="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/NRP_gurobi.py"

CPLEX_MP_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/MIP/main.py"

DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_${DATE_STR}.csv"
SHORTEN_RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_short_${DATE_STR}.csv"


mkdir -p "${SRC_PATH}/Compare_NRP/CSV/"

RESULT_DIR="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/Results"
METHOD="staircase_among"
TIMEOUT=300 # Thời gian chạy tối đa cho mỗi lệnh (giây)

# ==== Thông số chạy ====
NURSE_LIST=(30)
WEEK_LIST=(12 16 20 24)

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
  echo "nurses,week,model,encoding,clauses,vars,encoding_time,solving_time,total_time,validation" > "$RESULT_CSV"
fi

# Tạo file CSV rút gọn nếu chưa có
if [ ! -f "$SHORTEN_RESULT_CSV" ]; then
  echo "Creating shortened result CSV file..."
  echo "model,nurses,week,total_time" > "$SHORTEN_RESULT_CSV"
fi

# Tạo thư mục kết quả nếu chưa có
mkdir -p "$RESULT_DIR"
mkdir -p "tmp/solver_output/sat"
mkdir -p "tmp/solver_output/gurobi"
mkdir -p "tmp/solver_output/cplex_mp"

# ==== Chạy các tổ hợp ====
for NURSES in "${NURSE_LIST[@]}"; do
  for WEEKS in "${WEEK_LIST[@]}"; do
    echo "============================================"
    echo ">>> Running for $NURSES nurses and $WEEKS weeks..."
    echo ">>> Method: $METHOD"

    # Chạy script SAT
    echo "[SAT] Running..."
    source "$VENV_3_12_PATH"
    python3 "$SCRIPT1" "$NURSES" "$WEEKS" "$METHOD" "$RESULT_CSV" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${WEEKS}.txt"
    OUTPUT=$(timeout "$TIMEOUT" python3 "$SCRIPT1" "$NURSES" "$WEEKS" "$METHOD" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${WEEKS}.txt"

    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')

    echo "Total time for SAT: $total_time ms"
    echo "staircase_among,$NURSES,$WEEKS,$total_time" >> "$SHORTEN_RESULT_CSV"
    cleanup_memory

    # Chạy script Gurobi
    echo "[Gurobi] Running..."
    # python3 "$SCRIPT2" "$NURSES" "$WEEKS" "$RESULT_CSV" > "tmp/solver_output/gurobi/NRP_gurobi_${NURSES}_${WEEKS}.txt"
    OUTPUT=$(timeout "$TIMEOUT" python3 "$SCRIPT2" "$NURSES" "$WEEKS" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/gurobi/NRP_gurobi_${NURSES}_${WEEKS}.txt"

    total_time=$(echo "$OUTPUT" | grep "Total Time" | awk '{print $4}')
    echo "Total time for Gurobi: $total_time ms"
    echo "gurobi,$NURSES,$WEEKS,$total_time" >> "$SHORTEN_RESULT_CSV"
    cleanup_memory

    echo "[CPLEX MP] Running..."
    source "$VENV_3_8_PATH"
    OUTPUT=$(timeout "$TIMEOUT" python3 "$CPLEX_MP_SCRIPT" "$NURSES" "$WEEKS" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/cplex_mp/NRP_cplex_mp_${NURSES}_${WEEKS}.txt"
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${WEEKS}.txt"

    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    echo "Total time for CPLEX MP: $total_time ms"
    echo "cplex_mp,$NURSES,$WEEKS,$total_time" >> "$SHORTEN_RESULT_CSV"
  done
done

