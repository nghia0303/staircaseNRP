#!/bin/bash

# ==== Đường dẫn ====
VENV_3_12_PATH="/home/nghia/Desktop/Crew/staircase/venv/bin/activate"
VENV_3_8_PATH="/home/nghia/Desktop/Crew/staircase/venv4/bin/activate"
SRC_PATH="/home/nghia/Desktop/NRP_nghia"

SCRIPT1="${SRC_PATH}/src/test/run_nurse_rostering.py"
SCRIPT2="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/NRP_gurobi.py"

CPLEX_MP_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/MIP/main.py"
#CPLEX_CP_PATH="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/model/NRP.mod"
CPLEX_CP_PATH="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/model/nrp.py"
HADDOCK_CP_SCRIPT="${SRC_PATH}/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/sequenceNurse"
 #-w32 -m0 -n30 -d84
PICAT_PATH="${SRC_PATH}/Compare_NRP/Picat/model.pi"

DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_${DATE_STR}.csv"
SHORTEN_RESULT_CSV="${SRC_PATH}/Compare_NRP/CSV/result_short_${DATE_STR}.csv"


mkdir -p "${SRC_PATH}/Compare_NRP/CSV/"

RESULT_DIR="${SRC_PATH}/Compare_NRP/Gurobi-For-NRP/Gurobi/Results"
METHOD="staircase_among"
TIMEOUT=600 # Thời gian chạy tối đa cho mỗi lệnh (giây)

# ==== Thông số chạy ====
NURSE_LIST=(30 40 50 60 80 100 120)
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

    cleanup_memory
    echo "============================================"
    # Chạy script SAT
    echo "[SAT] Running..."
    source "$VENV_3_12_PATH"
    python3 "$SCRIPT1" "$NURSES" "$DAYS" "$METHOD" "$RESULT_CSV" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$SCRIPT1" "$NURSES" "$DAYS" "$METHOD" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for SAT: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "staircase_among,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"


    # Chạy script Gurobi
    echo "[Gurobi] Running..."
    cleanup_memory
    # python3 "$SCRIPT2" "$NURSES" "$DAYS" "$RESULT_CSV" > "tmp/solver_output/gurobi/NRP_gurobi_${NURSES}_${DAYS}.txt"
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$SCRIPT2" "$NURSES" "$DAYS" "$RESULT_CSV" 2>&1)
    echo "$OUTPUT" > "tmp/solver_output/gurobi/NRP_gurobi_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total Time" | awk '{print $4}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for Gurobi: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "gurobi,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"


    echo "[CPLEX MP] Running..."
    cleanup_memory
    source "$VENV_3_8_PATH"
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$CPLEX_MP_SCRIPT" "$NURSES" "$DAYS" 2>&1)

    echo "$OUTPUT" > "tmp/solver_output/cplex_mp/NRP_cplex_mp_${NURSES}_${DAYS}.txt"
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"

    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for CPLEX MP: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "cplex_mp,$NURSES,$DAYS,$total_time" >> "$SHORTEN_RESULT_CSV"

    echo "[CPLEX CP] Running..."
    cleanup_memory
    source "$VENV_3_8_PATH"
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" python3 "$CPLEX_CP_PATH" "$NURSES" "$DAYS" 2>&1)

    echo "$OUTPUT" > "tmp/solver_output/cplex_mp/NRP_cplex_cp_${NURSES}_${DAYS}.txt"
    echo "$OUTPUT" > "tmp/solver_output/sat/NRP_sat_${NURSES}_${DAYS}.txt"

    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Total time:" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')

    echo "Total time for CPLEX CP: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "cplex_cp,$NURSES,$DAYS,$total_time" >> "$SHORTEN_RESULT_CSV"

    echo "[HADDOCK classic CP] Running..."
    cleanup_memory
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" "$HADDOCK_CP_SCRIPT" -w64 -m0 -n"$NURSES" -d"$DAYS" 2>&1)
#    echo "$OUTPUT"
    echo "$OUTPUT" > "tmp/solver_output/cplex_cp/NRP_haddock_cp_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Time :" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')
    echo "Total time for HADDOCK classic CP: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "haddock_classic,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"
#
    echo "[HADDOCK seqMDD2 CP] Running..."
    cleanup_memory
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" "$HADDOCK_CP_SCRIPT" -w64 -m2 -n"$NURSES" -d"$DAYS" 2>&1)
#    echo "$OUTPUT"
    echo "$OUTPUT" > "tmp/solver_output/cplex_cp/NRP_haddock_cp_${NURSES}_${DAYS}.txt"
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    total_time=$(echo "$OUTPUT" | grep "Time :" | awk '{print $3}')
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')
    echo "Total time for HADDOCK seqMDD2 CP: $total_time ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "haddock_seqMDD2,$NURSES,$DAYS,$total_time,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"


    echo "[Picat] Running..."
    START_TIME=$(date +%s%N)
    mem_file=$(mktemp)
    OUTPUT=$(/usr/bin/time -f "%M" -o "$mem_file" timeout "$TIMEOUT" picat "$PICAT_PATH" "$NURSES" "$DAYS")
    PEAK_RAM=$(cat "$mem_file"); rm -f "$mem_file"
    END_TIME=$(date +%s%N)
    ELAPSED_TIME=$((($END_TIME - $START_TIME)/1000000)) # Convert nanoseconds to milliseconds
    solns=$(echo "$OUTPUT" | grep "solns:" | awk '{print $2}')
    echo "Total time for Picat: $ELAPSED_TIME ms"
    echo "Solutions found: $solns"
    echo "Peak RAM: $PEAK_RAM KB"
    echo "picat,$NURSES,$DAYS,$ELAPSED_TIME,$PEAK_RAM,$solns" >> "$SHORTEN_RESULT_CSV"
  done
done

