# Chạy riêng TabularAllSAT cho amongNurse

Đây là lượt chạy thử AllSAT trên model legacy `src/test/NRP_2010.py`, **không** thay thế runner thực nghiệm mới trong `experiments/` và không tự đưa số đo WSL vào paper. Không commit source/binary của solver bên thứ ba vào repo này.

## Cài trên máy Ubuntu chạy thực nghiệm

Từ **gốc monorepo `SequenceConstraint`** sau khi pull code:

```bash
sudo apt-get update
sudo apt-get install -y git build-essential libgmp-dev runlim coreutils
source code/staircaseNRP/scripts/linux_env.sh
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

Python cần môi trường Linux của dự án (`NRP_VENV` trong `scripts/linux_env.sh`) với `python-sat` và các dependency tại `requirements-linux.lock.txt`. Nếu máy chưa thiết lập môi trường, xem [WSL_ENVIRONMENT.md](WSL_ENVIRONMENT.md) và chạy `bash code/staircaseNRP/scripts/setup_linux.sh` từ gốc monorepo; không dùng virtualenv Windows.

## Chạy

Từ bất kỳ thư mục nào sau khi đã `source code/staircaseNRP/scripts/linux_env.sh` từ gốc monorepo:

```bash
# Mặc định: C-III, H=40; chạy Ladder rồi DE, liệt kê các lịch đầy đủ
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh"

# Chỉ định một instance
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 2 40

# Quét đủ 15 cấu hình cho cả Ladder và DE, có thể rất lâu
bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" --grid
```

`ALLSAT_TIMEOUT_S=300` và `ALLSAT_MEMORY_MB=4096` là giới hạn mặc định **cho từng method/instance**; chỉnh bằng biến môi trường khi cần. `ALLSAT_OUTPUT_ROOT` đổi nơi lưu kết quả; mặc định là `tmp/amongNurse-allsat/` ở gốc monorepo, đã bị Git ignore. Mỗi lượt tạo CNF projected, JSON report, stdout và log runlim riêng. Nếu một lượt timeout/lỗi, script vẫn chạy các lượt còn lại, giữ log, rồi trả exit code 1 ở cuối. Không dùng `sudo`, không xóa cache máy, không sửa script benchmark cũ.

Muốn kiểm tra từng lịch và tính duy nhất ngoài việc đối chiếu số dòng, bật validator; thời gian sẽ gồm thêm overhead Python:

```bash
ALLSAT_VALIDATE_MODELS=1 bash "$SRC_PATH/Compare_NRP_2010/run_all_sat.sh" 3 40
```

Runner gọi `--enum_total` và chiếu lên **H biến ngày làm/nghỉ**, nên một nghiệm là một lịch, không phải một phép gán cho các biến phụ. Solver trả exit code `20` khi đã liệt kê xong; wrapper chỉ coi lượt chạy hoàn tất khi có `s MODEL COUNT` và số dòng nghiệm khớp con số báo cáo. Mốc `solver_wall_s_including_pipe` tính cả việc chuyển/đọc stdout (và validation nếu bật), không phải thời gian CPU thuần của solver. `encoding_wall_s` được ghi riêng. Số đo chính thức chỉ lấy trên cùng máy Ubuntu và cùng cấu hình đã ghim.

Model và encoding được lấy trực tiếp từ `NRP_2010.NRP`: **Ladder = `staircase-binomial`**, **DE = `pblib_bdd-binomial`** như bảng amongNurse của paper hiện tại. Phần đầu mã hóa các cửa sổ trượt; `binomial` mã hóa giới hạn 4–5 ngày làm mỗi **tuần lịch đầy đủ**, giống nhau ở hai method. Script legacy `run.sh` còn thử `pblib_bdd-pblib_bdd`, nhưng đó không phải cấu hình DE trong bảng paper. Wrapper chỉ thêm định dạng projected DIMACS mà TabularAllSAT cần: `p cnf <nvars> <nclauses> <H>` và dòng `c p show 1 ... H` (không có số 0 cuối). `NRP_2010.to_cnf()` cũ là DIMACS thường nên không đủ để yêu cầu chiếu lên lịch ngày. Không sửa `NRP_2010.py` hoặc vòng PySAT cũ.

Smoke test trên WSL: Ladder và DE đều xuất C-I/H=40: 2.284 lịch, C-II/H=40: 3 lịch, C-III/H=40: 137.593 lịch. Tất cả lịch xuất ra trong các lượt này đã được kiểm tra thỏa đặc tả và không trùng; số đếm khớp bảng amongNurse-all hiện có của paper. Đây chỉ là kiểm tra chức năng, chưa phải so sánh hiệu năng công bằng với phương pháp khác.
