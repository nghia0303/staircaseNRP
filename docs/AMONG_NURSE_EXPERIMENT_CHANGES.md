# Cập nhật runner thực nghiệm AmongNurse

Tài liệu này tóm tắt các thay đổi thực hiện trong tháng 9/2026 cho hai bài
toán tìm một nghiệm và liệt kê toàn bộ nghiệm. Các số đo hiện tại dùng để kiểm
tra runner; cần chạy lại với số lần lặp đã định trước trước khi đưa vào paper.

## AllSAT

- `Compare_NRP_2010/run_all_sat.sh` chạy đủ C-I, C-II, C-III và các horizon
  40, 50, 60, 70, 80. Runner có các chế độ `--ci-cii`, `--ciii`, `--grid` và
  một cặp `CLASS HORIZON`.
- Ba encoding SAT được chạy với G421, CaDiCaL 1.9.5 và CaDiCaL 3.0. Các phương
  pháp TabularAllSAT và các phương pháp legacy trong `run.sh` vẫn được giữ lại.
- `run_all_sat_ci_cii.sh` và `run_all_sat_ci_cii_ciii.sh` là hai entrypoint cho
  hai grid thường dùng.
- Mỗi lượt lưu JSON, stdout, stderr, log runlim và `summary.csv`. GNU wall time
  bao ngoài runlim; runlim ghi CPU time và peak RAM. RAM mặc định bằng RAM máy
  trừ 6 GiB.

## OneSAT

- `run_one_solution_ci_cii_ciii.py` là runner chính. `method_wall_s` dùng
  `time.perf_counter_ns()` quanh toàn bộ process của một method, gồm process
  startup, import, encoding, solve và shutdown.
- Runner hỗ trợ `--grid`, `--ci-cii`, một cặp `CLASS HORIZON`,
  `--repetitions`, `--methods` và `--include-private`. Kết quả được ghi vào
  `summary.csv`; nhiều lần lặp có thêm `summary_aggregate.csv`.
- `run_one_solution_ci_cii_ciii.sh` chỉ chuyển tiếp tham số sang runner Python
  để hai entrypoint dùng cùng một cách đo.
- `time_method_process.py` giữ biên đo process độc lập với runlim.

## Giảm startup của SAT

- Các encoding, `openpyxl`, public `pysat.solvers.Solver` và LocalSolver được
  import khi thực sự cần. Các import cũ được giữ dưới dạng comment cạnh code
  mới.
- Full garbage collection trong hai vòng tạo ràng buộc chỉ chạy khi đặt
  `NRP_FORCE_GC=1`.
- `NRP_2010_pysolvers_private.py` cung cấp adapter thử nghiệm trực tiếp tới
  private `pysolvers` cho G421, CaDiCaL 1.9.5 và CaDiCaL 3.0. Adapter này chỉ
  được thêm vào grid khi dùng `--include-private`.
- Môi trường Python mặc định là `.venv` trong repo; `.venv/` được ignore.

## Kiểm tra đã thực hiện

- CNF fingerprint không đổi sau khi chuyển sang lazy import.
- 135/135 nghiệm từ ba private backend hợp lệ trên 15 instance và ba encoding.
- Grid OneSAT có private API hoàn tất 375/375 lượt.
- Private API nhanh hơn public API trên 135/135 cặp đã đo.

## Solver dùng thống nhất

CaDiCaL 1.9.5 được chọn làm SAT backend chính cho cả OneSAT và AllSAT. Với
Staircase, G421 nhanh hơn khoảng 5.6% trên grid OneSAT một lần lặp, nhưng
CaDiCaL 1.9.5 hoàn tất toàn bộ AllSAT C-III trong khi G421 timeout tại H50 và
H60. G421 và CaDiCaL 3.0 vẫn có trong runner để kiểm tra độ nhạy theo solver.

## Lệnh chính

```bash
cd /home/nghia/Desktop/Staircase/staircaseNRP

# AllSAT: đủ C-I, C-II, C-III
NRP_VENV="$PWD/.venv" ALLSAT_PYTHON_BIN="$PWD/.venv/bin/python" \
  bash Compare_NRP_2010/run_all_sat_ci_cii_ciii.sh

# OneSAT: đủ grid, có cả private API
.venv/bin/python -B Compare_NRP_2010/run_one_solution_ci_cii_ciii.py \
  --grid --include-private --repetitions 1
```
