#!/bin/bash

# ==== Đường dẫn ====
VENV_PATH="/home/nghia/Desktop/Crew/staircase/venv/bin/activate"

SRC_PATH="/home/nghia/Desktop/NRP_nghia"

SCRIPT1="${SRC_PATH}/src/test/run_nurse_rostering.py"
SCRIPT2="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/NRP_gurobi.py"

DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_${DATE_STR}.csv"

mkdir -p "${SRC_PATH}/Compare_NRP/CSV/"

RESULT_DIR="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/Results"
METHOD="pblib_bdd"

# ==== Thông số chạy ====
NURSE_LIST=(100)
WEEK_LIST=(16 20 24)

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
source "$VENV_PATH"

# Tạo file CSV nếu chưa có
if [ ! -f "$RESULT_CSV" ]; then
  echo "Creating result CSV file..."
  echo "nurses,week,model,encoding,clauses,vars,encoding_time,solving_time,total_time,validation" > "$RESULT_CSV"
fi

# Tạo thư mục kết quả nếu chưa có
mkdir -p "$RESULT_DIR"
mkdir -p "tmp/solver_output/sat"
mkdir -p "tmp/solver_output/gurobi"


# ==== Chạy các tổ hợp ====
for NURSES in "${NURSE_LIST[@]}"; do
  for WEEKS in "${WEEK_LIST[@]}"; do
    echo "============================================"
    echo ">>> Running for $NURSES nurses and $WEEKS weeks..."
    echo ">>> Method: $METHOD"

    # Chạy script SAT
    echo "[SAT] Running..."
    python3 "$SCRIPT1" "$NURSES" "$WEEKS" "$METHOD" "$RESULT_CSV" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${WEEKS}.txt"
    cleanup_memory

    # Chạy script Gurobi
#    echo "[Gurobi] Running..."
#    python3 "$SCRIPT2" "$NURSES" "$WEEKS" "$RESULT_CSV" > "tmp/solver_output/gurobi/NRP_gurobi_${NURSES}_${WEEKS}.txt"
#    cleanup_memory

  done
done

