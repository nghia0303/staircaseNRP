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
PICAT_PATH="/home/nghia/Desktop/NRP_nghia/Compare_NRP_2010/Picat/sample.pi"

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
C_LIST=(2)
H_LIST=(80)
R_LIST=(1)
I_LIST=(1)


# Chạy script AmongNurse
#"$AMONG_NURSE_SCRIPT" -w128 -m2 -r2147483647 -i2147483647 -c1 -h
for C in "${C_LIST[@]}"; do
  for H in "${H_LIST[@]}"; do

    # Run MDD
#    for R in "${R_LIST[@]}"; do
#      for I in "${I_LIST[@]}"; do
#        for W in "${W_LIST[@]}"; do
#          for M in "${M_LIST[@]}"; do
#            echo "============================================"
#            echo ">>> Running for W=$W, M=$M, R=$R, I=$I C=$C, H=$H..."
#
#            # Chạy script AmongNurse
#            echo "[AmongNurse] Running..."
#            OUTPUT=$("$AMONG_NURSE_SCRIPT" -w"$W" -m"$M" -r"$R" -i"$I" -c"$C" -h"$H")
#
#            TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
#            TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
#            SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')
#
#            echo "Time: $TIME"
#            echo "Time to First Solution: $TIME_TO_FIRST_SOL"
#            echo "Solutions: $SOLNS"
#            # Ghi kết quả vào file CSV
#            echo "MDD,$W,$M,$R,$I,$C,$H,$TIME,$TIME_TO_FIRST_SOL,$SOLNS" >> "$RESULT_CSV"
#
# 95310

#            cleanup_memory
#
#
#          done
#        done
#      done
#    done
    # Run Staircase

    # Try best MDD configuration based on 2022 paper

    echo "${C} ${H}"
    echo "============================================"
    OUTPUT=$("$AMONG_NURSE_SCRIPT" -w64 -m0 -r5 -i10 -c"$C" -h"$H" -n0 -na1 -d2 -ca1 -a1 -e1 -p0 -t3 -maxP0 -minP0 -wP0 -j1)

    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
            # Ghi kết quả vào file CSV
    echo "MDD,64,0,$C,$H,$TIME,$TIME_TO_FIRST_SOL,$SOLNS" >> "$RESULT_CSV"

    echo "${C} ${H}"
    echo "============================================"
    OUTPUT=$(timeout 300 "$AMONG_NURSE_SCRIPT" -w64 -m1 -r5 -i10 -c"$C" -h"$H" -n0 -na1 -d2 -ca1 -a1 -e1 -p0 -t3 -maxP0 -minP0 -wP0 -j1)

    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
            # Ghi kết quả vào file CSV
    echo "MDD,64,1,$C,$H,$TIME,$TIME_TO_FIRST_SOL,$SOLNS" >> "$RESULT_CSV"
    echo "============================================"
    echo "Staircase"
    source "$VENV_3_12_PATH"
    OUTPUT=$(timeout 300 python3 "$STAIRCASE_PATH" "$H" "$C" "staircase" "m22")
    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "Staircase,,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"

    echo ""
    echo ""

    echo "============================================"
    echo "CPLEX CP"
    source "$VENV_3_8_PATH"
    OUTPUT=$(timeout 300 python3 "$CPLEX_CP_PATH" "$H" "$C")
    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "CPLEX_CP,,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"

    echo ""
    echo ""

    echo "============================================"
    echo "CPLEX MP"
    OUTPUT=$(timeout 300 python3 "$CPLEX_MP_PATH" "$H" "$C")
    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "CPLEX_MP,,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"

    echo ""
    echo ""

    echo "============================================"
    echo "Gurobi"
    OUTPUT=$(timeout 300 python3 "$GUROBI_PATH" "$H" "$C")
    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $TIME"
    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "Gurobi,,$C,$H,$TIME,,$SOLNS" >> "$RESULT_CSV"

    echo ""
    echo ""

    echo "============================================"
    echo "Picat"
    START_TIME=$(date +%s%N)
    OUTPUT=$(timeout 300 picat "$PICAT_PATH" "$C" "$H")
    END_TIME=$(date +%s%N)
    ELAPSED_TIME=$((($END_TIME - $START_TIME)/1000000)) # Convert nanoseconds to milliseconds
#    TIME=$(echo "$OUTPUT" | grep '"time" :' | awk '{print $3}' | tr -d ',')
#    TIME_TO_FIRST_SOL=$(echo "$OUTPUT" | grep 'timeToFirstSol' | awk '{print $3}' | tr -d ',')
    SOLNS=$(echo "$OUTPUT" | grep 'solns' | awk '{print $3}' | tr -d ',')

    echo "Time: $ELAPSED_TIME"
#    echo "Time to First Solution: $TIME_TO_FIRST_SOL"
    echo "Solutions: $SOLNS"
    # Ghi kết quả vào file CSV
    echo "Picat,,$C,$H,$ELAPSED_TIME,,$SOLNS" >> "$RESULT_CSV"

    echo ""
    echo ""

  done
done
