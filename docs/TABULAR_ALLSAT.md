# Chạy amongNurse với TabularAllSAT và các phương pháp legacy

`Compare_NRP_2010/run_all_sat.sh` chạy các phương pháp và tham số của `run.sh`, đồng thời chạy cả ba cấu hình SAT bằng TabularAllSAT **và** PySAT `g421` trên model legacy `src/test/NRP_2010.py`. `run.sh` vẫn giữ nguyên. Không tự đưa số đo WSL vào paper. Không commit source/binary của solver bên thứ ba vào repo này.

## Cài trên máy Ubuntu chạy thực nghiệm

Từ **gốc repo `staircaseNRP`** sau khi pull code:

```bash
sudo apt-get update
sudo apt-get install -y git build-essential libgmp-dev runlim coreutils
source scripts/linux_env.sh
mkdir -p "$NRP_NATIVE_HOME/src"
git clone https://github.com/giuspek/tabularAllSAT.git "$NRP_NATIVE_HOME/src/tabularAllSAT"
git -C "$NRP_NATIVE_HOME/src/tabularAllSAT" checkout --detach ad4a071310581990b7834f1f076ccfb54d592bbf
git -C "$NRP_NATIVE_HOME/src/tabularAllSAT" rev-parse HEAD
cd "$NRP_NATIVE_HOME/src/tabularAllSAT/cdcl-vsads"
./configure
make -j2
./solver --version
```

Commit bắt buộc: `ad4a071310581990b7834f1f076ccfb54d592bbf` của [giuspek/tabularAllSAT](https://github.com/giuspek/tabularAllSAT). Lệnh `rev-parse HEAD` phải in đúng commit đó. Nếu thư mục cài đã tồn tại, **không clone đè**: kiểm tra commit và trạng thái source trước khi dùng. Máy đã cài MiniCPP/Picat không mặc nhiên có TabularAllSAT. Binary mặc định được runner tìm tại `$NRP_NATIVE_HOME/src/tabularAllSAT/cdcl-vsads/solver`; có thể chỉ đường dẫn khác qua `TABULAR_ALLSAT_BIN`. Report mỗi lượt ghi SHA256 binary, CNF và các file model/encoding chính để đối chiếu hai máy.

Python cần môi trường Linux của dự án (`NRP_VENV` trong `scripts/linux_env.sh`) với `python-sat` và các dependency tại `requirements-linux.lock.txt`. Nếu máy chưa thiết lập môi trường, xem [WSL_ENVIRONMENT.md](WSL_ENVIRONMENT.md) và chạy `bash scripts/setup_linux.sh` từ gốc repo; không dùng virtualenv Windows.

## Chạy

Từ bất kỳ thư mục nào sau khi đã `source scripts/linux_env.sh` từ gốc repo:

```bash
# Mặc định: C-III, H=40; chạy đủ 13 phương pháp
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh"

# Chỉ định một instance
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 2 40

# Quét đủ 15 cấu hình cho cả 13 phương pháp, có thể rất lâu
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" --grid

# Chạy riêng các cấu hình SAT qua TabularAllSAT
ALLSAT_METHODS="ladder pblib_bdd-pblib_bdd de" bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 2 40

# Chạy riêng ba cấu hình SAT qua PySAT g421
ALLSAT_METHODS="sat_g421_staircase-binomial sat_g421_pblib_bdd-pblib_bdd sat_g421_pblib_bdd-binomial" bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 2 40
```

Ba cấu hình TabularAllSAT là `ladder` = `staircase-binomial`, `pblib_bdd-pblib_bdd` và `de` = `pblib_bdd-binomial`. Ba cấu hình PySAT `g421` tương ứng có tiền tố `sat_g421_`; chúng gọi `NRP_2010.py` với tên solver `g421` và liệt kê nghiệm bằng vòng SAT tăng dần. Bảy phương pháp còn lại là `classic`, `amongMDD2`, `seqMDD2`, `CPLEX_CP`, `CPLEX_MP`, `Gurobi`, `Picat`; chúng dùng cùng model và tham số như `run.sh`. `ALLSAT_METHODS` nhận danh sách tên cách nhau bằng dấu cách nếu chỉ muốn chạy một phần. Nếu có một lượt TabularAllSAT hoàn tất trước các phương pháp khác, runner dùng số lịch đó để phát hiện sai lệch số nghiệm.

Trên màn hình, mỗi lượt có số thứ tự, C/H và tên phương pháp, sau đó là trạng thái, số nghiệm, thời gian toàn lượt và RAM tối đa. Thông báo terminal chỉ dùng ký tự ASCII để tránh lỗi font. Thời gian này là `GNU wall`, đo bằng `/usr/bin/time -f '%e'` bao ngoài runlim; `runlim wall`, CPU và các thời gian nội bộ nằm trong `summary.csv` và log riêng. Khi lỗi, màn hình chỉ tên report và log trong thư mục output; stdout chi tiết của chương trình được lưu vào file để dễ xem lại.

`ALLSAT_TIMEOUT_S=300` là giới hạn thời gian mặc định **cho từng method/instance**. Giới hạn RAM mặc định lấy tổng RAM Ubuntu nhận được trừ 6144 MiB (6 GiB) cho hệ điều hành và tiến trình nền; trên máy Ubuntu 32028 MiB hiện tại là **25884 MB mỗi lượt** qua `runlim -s`. Có thể đặt giới hạn khác bằng `ALLSAT_MEMORY_MB`. Đây là mức trần của lượt chạy, không phải phần RAM được hệ điều hành giữ riêng. `ALLSAT_OUTPUT_ROOT` đổi nơi lưu kết quả; mặc định là `tmp/amongNurse-allsat/` ở gốc repo `staircaseNRP`, đã bị Git ignore. Mỗi lượt có JSON report, stdout, stderr, log runlim và file `.gnu_time.txt` riêng; ba lượt TabularAllSAT còn tạo CNF projected. `summary.csv` tổng hợp các phương pháp, giữ riêng thời gian nội bộ, `runlim_real_s` và `gnu_time_real_s` đo bằng `/usr/bin/time -f '%e'` bao ngoài runlim. Mỗi lần chạy tạo thư mục output mới. Nếu một lượt timeout/lỗi, script vẫn chạy các lượt còn lại, giữ log, rồi trả exit code 1 ở cuối. Runner không dùng `sudo` hoặc xóa cache máy.

Muốn kiểm tra từng lịch và tính duy nhất của ba lượt TabularAllSAT ngoài việc đối chiếu số dòng, bật validator; thời gian sẽ gồm thêm overhead Python:

```bash
ALLSAT_VALIDATE_MODELS=1 bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 3 40
```

Runner gọi `--enum_total` và chiếu lên **H biến ngày làm/nghỉ**, nên một nghiệm là một lịch, không phải một phép gán cho các biến phụ. Solver trả exit code `20` khi đã liệt kê xong; wrapper chỉ coi lượt chạy hoàn tất khi có `s MODEL COUNT` và số dòng nghiệm khớp con số báo cáo. Mốc `solver_wall_s_including_pipe` tính cả việc chuyển/đọc stdout (và validation nếu bật), không phải thời gian CPU thuần của solver. `encoding_wall_s` được ghi riêng. Số đo chính thức chỉ lấy trên cùng máy Ubuntu và cùng cấu hình đã ghim.

Model và encoding được lấy trực tiếp từ `NRP_2010.NRP`: **Ladder = `staircase-binomial`**, **DE = `pblib_bdd-binomial`** như bảng amongNurse của paper hiện tại. Cấu hình thứ ba `pblib_bdd-pblib_bdd` cũng được chạy qua TabularAllSAT để khớp danh sách của `run.sh`; đó là cấu hình riêng, không phải DE trong bảng paper. Phần đầu mã hóa các cửa sổ trượt; `binomial` mã hóa giới hạn 4–5 ngày làm mỗi **tuần lịch đầy đủ**. Wrapper thêm định dạng projected DIMACS mà TabularAllSAT cần: `p cnf <nvars> <nclauses> <H>` và dòng `c p show 1 ... H` (không có số 0 cuối). `NRP_2010.to_cnf()` cũ là DIMACS thường nên không đủ để yêu cầu chiếu lên lịch ngày. Không sửa `NRP_2010.py` hoặc vòng PySAT cũ.

Smoke test trên WSL: Ladder và DE đều xuất C-I/H=40: 2.284 lịch, C-II/H=40: 3 lịch, C-III/H=40: 137.593 lịch. Tất cả lịch xuất ra trong các lượt này đã được kiểm tra thỏa đặc tả và không trùng; số đếm khớp bảng amongNurse-all hiện có của paper. Đây chỉ là kiểm tra chức năng, chưa phải so sánh hiệu năng công bằng với phương pháp khác.
