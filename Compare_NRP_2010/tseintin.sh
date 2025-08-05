#!/bin/bash

# ==== Đường dẫn ====
VENV_PATH="/home/nghia/Desktop/Crew/staircase/venv/bin/activate"

SRC_PATH="/home/nghia/Desktop/NRP_nghia"

AMONG_NURSE_SCRIPT="/home/nghia/Desktop/NRP_nghia/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/amongNurse"
STAIRCASE_PATH="/home/nghia/Desktop/NRP_nghia/src/test/NRP_2010.py"

SOLVER="cd195"  # Chọn solver cd195
DATE_STR=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${SRC_PATH}/Compare_NRP_2010/CSV/tseintin_${SOLVER}_${DATE_STR}.csv"
mkdir -p "${SRC_PATH}/Compare_NRP_2010/CSV/"

cleanup_memory() {
  echo "Cleaning memory cache..."
  sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
}


# Write header to CSV file
echo "width,C,H,totalTime,timeToFirstSol,Sols" > "$RESULT_CSV"

sudo -v

chmod +x "$AMONG_NURSE_SCRIPT"

source "$VENV_PATH"

W_LIST=(10 15 20 25 30 40)
M_LIST=(0)
C_LIST=(1 2 3)
H_LIST=(40 50 60 70 80)
R_LIST=(1)
I_LIST=(1)



# Chạy script AmongNurse

for C in "${C_LIST[@]}"; do
  for H in "${H_LIST[@]}"; do
    echo "============================================"
    echo "$C $H"

    echo "None Tseintin"
    OUTPUT=$(timeout 300 python3 "$STAIRCASE_PATH" "$H" "$C" "staircase" "$SOLVER" "false")
    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "None,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"
    echo ""
    echo ""


    for W in "${W_LIST[@]}"; do
      echo "============================================"
      echo "Tseintin $W"
      OUTPUT=$(timeout 300 python3 "$STAIRCASE_PATH" "$H" "$C" "staircase" "$SOLVER" "false" "true" "$W")
      TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
      TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
      SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

      echo "Time: $TIME"
      echo "Time to First Solution: $TIME_TO_FIRST_SOL"
      echo "Solutions: $SOLNS"
      # Ghi kết quả vào file CSV
      echo "$W,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"
      echo ""
      echo ""
    done

  done
done
