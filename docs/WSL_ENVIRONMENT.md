# Môi trường Linux cho phát triển và debug

Cập nhật 2026-09-21. **Đã cài và kiểm tra môi trường Python/SAT và toolchain C++ trong WSL.** Đây là môi trường phát triển; chưa chứng nhận toàn bộ tám method hoặc đồng nhất với máy Ubuntu ở nhà.

## Quyết định làm việc

Dùng WSL 2 trên máy Windows để code, build, debug và chạy thử. Push code đã kiểm tra lên Git; máy Ubuntu ở nhà pull, thiết lập/build bằng script và chạy thực nghiệm, không sửa source trên máy đó. Số đo chính thức lấy trên máy Ubuntu ở nhà.

## Địa chỉ môi trường local

- Distro: Ubuntu-26.04, Ubuntu 26.04.1 LTS, WSL 2.
- User Linux: nghia; Python hệ thống đã kiểm tra: 3.14.4.
- Source Windows: D:\Research\SequenceConstraint\code\staircaseNRP.
- Cùng source trong WSL: /mnt/d/Research/SequenceConstraint/code/staircaseNRP.
- Virtualenv Linux: /home/nghia/.venvs/sequenceconstraint.
- Các môi trường .venv và .venv310 của workspace Windows là môi trường cũ riêng biệt; không dùng chúng để chạy Linux.

Tạm dùng một working tree chung để mọi chỉnh sửa ở máy này thấy ngay trong WSL. Virtualenv đặt trên filesystem Linux. Khi cần tối ưu I/O cho build lớn, có thể thống nhất chuyển working tree vào filesystem Linux; hiện chưa tạo clone thứ hai.

## Gọi từ PowerShell

```powershell
wsl.exe -d Ubuntu-26.04 --cd /mnt/d/Research/SequenceConstraint/code/staircaseNRP --exec /home/nghia/.venvs/sequenceconstraint/bin/python -B sequence_nurse_dataset/generate.py --dry-run
```

Lệnh trên chỉ xem cấu hình, không sinh dataset. Dataset v1 vẫn chờ tác giả duyệt script.

## Phạm vi đồng bộ

Theo yêu cầu cập nhật, lấy bản thư viện mới nhất tương thích mà pip tìm được tại thời điểm thiết lập, rồi kiểm tra thực tế. File requirements.txt gốc ghi dependency cũ, được giữ làm tham chiếu; không dùng nó để cài đè lên môi trường WSL mới.

| Thành phần | Phiên bản đã kiểm tra |
|---|---|
| Python Linux | 3.14.4, do Ubuntu cung cấp |
| python-sat / pypblib | 1.9.dev15 / 0.0.4 |
| psutil / openpyxl | 7.2.2 / 3.1.5 |
| NumPy / pandas / SciPy | 2.5.3 / 3.0.6 / 1.18.1 |
| docplex / cplex (metadata pip) | 2.32.264 / 22.2.0.1 |
| CPLEX engine từ Studio / CP Optimizer | Studio 22.2, engine CPLEX báo 22.2.0.0; xem CPLEX_CHECK.json |
| gurobipy | 13.0.3 |
| GCC / Clang | 15.2.0 / 21.1.8 |
| CMake / GDB / runlim | 4.2.3 / 17.1 / 1.10 |

Đã cài các tên gói trong requirements.txt cũ bằng phiên bản tương thích mới, bổ sung cplex. Danh sách chính xác nằm trong [requirements-linux.lock.txt](../requirements-linux.lock.txt); danh sách yêu cầu trước khi khóa nằm trong [requirements-linux.in](../requirements-linux.in).

**Ngoại lệ đã có lỗi thực tế:** setuptools 84.0.0 làm import stopit 1.1.2 thất bại với ModuleNotFoundError: pkg_resources. Đã dùng bản mới nhất dưới 82 là setuptools 81.0.0, rồi kiểm tra lại thành công. stopit vẫn phát cảnh báo deprecated; không sửa source thư viện. Việc loại pkg_resources từ 82 được xác nhận trong [release notes chính thức](https://setuptools.pypa.io/en/stable/history.html#v82-0-0).

## Thiết lập lại trên Linux

Cài dependency hệ thống bằng tài khoản quản trị (trên WSL có thể dùng wsl.exe -d Ubuntu-26.04 -u root --exec apt-get ... từ PowerShell):

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git python3-dev python3-venv pkg-config libgmp-dev zlib1g-dev curl ca-certificates time runlim
sudo apt-get install -y --no-install-recommends clang gdb pybind11-dev
```

Sau đó, từ gốc repo:

```bash
bash scripts/setup_linux.sh
$HOME/.venvs/sequenceconstraint/bin/python -B scripts/check_linux_environment.py --output tmp/linux-environment-check.json
```

Khi làm việc trong terminal WSL, kích hoạt môi trường bằng source "$HOME/.venvs/sequenceconstraint/bin/activate". Khi đó python và pip trỏ vào virtualenv Linux; các lệnh từ PowerShell nên tiếp tục dùng đường dẫn interpreter đầy đủ ở trên.

setup_linux.sh tạo/cài virtualenv riêng và ưu tiên bản khóa. Có thể chỉ định interpreter bằng PYTHON_BIN và nơi đặt virtualenv bằng NRP_VENV, ví dụ:

```bash
PYTHON_BIN=python3.14 NRP_VENV="$HOME/.venvs/sequenceconstraint" bash scripts/setup_linux.sh
```

Profile này yêu cầu Python 3.12 trở lên; chỉ Python 3.14.4/Linux x86_64 đã được kiểm chứng ở đây. Khuyến nghị thống nhất Python 3.14 ở hai máy; không tự thay Python hệ thống của máy Ubuntu cũ. Các gói apt lấy phiên bản của distro đang dùng nên không bảo đảm compiler giống nhau chỉ bằng cùng tên gói.

Muốn nâng dependency trong lần sau: dùng pip install --upgrade -r requirements-linux.in, chạy lại script kiểm tra, rồi mới cập nhật bản khóa bằng pip freeze --all. Không tự nâng riêng một máy sau khi đã chốt batch thực nghiệm.

## Bằng chứng kiểm tra và giới hạn

[WSL_ENVIRONMENT_CHECK.json](WSL_ENVIRONMENT_CHECK.json) lưu phiên bản và kết quả kiểm tra:

- Import các thư viện tính toán, xử lý file và solver Python đều thành công; pip check không báo dependency hỏng.
- pypblib cài trực tiếp bằng pip, pip tự build wheel Linux, không sửa mã thư viện. Mã hóa BDD qua PBEnc được kiểm tra cả SAT và UNSAT.
- Ladder và DE: C-II, H=40 đều liệt kê đúng 3 lịch bằng code hiện có. Một nghiệm mỗi encoding được kiểm tra trực tiếp các cửa sổ và tuần lịch. Đây là smoke test môi trường, chưa phải audit toàn bộ encoding.
- Glucose 4.2.1 warm_start chạy được trên công thức nhỏ. Chưa sửa vòng AllSAT hoặc bật warm_start cho các method hiện tại.
- GCC và Clang đều build/chạy được chương trình C++17. MiniCPP/HADDOCK đã được build Release bằng GCC, ghim commit và patch riêng; xem [NATIVE_SOLVERS.md](NATIVE_SOLVERS.md).
- runlim chạy được, lấy mẫu RAM của tiến trình thử; chưa kiểm tra đầy đủ mọi tình huống timeout/MEMOUT của runner.
- CPLEX-MP qua docplex và Gurobi đều giải được model nhị phân nhỏ. Sau khi cài Studio, CPLEX-MP và CP Optimizer còn giải được model 1.100 biến; xem CPLEX_CHECK.json. Gurobi chưa kiểm tra vượt giới hạn model nhỏ. Chưa kiểm tra toàn bộ instance thực nghiệm.
- Picat 3.9#12 và ba executable MiniCPP đã cài; dùng `source scripts/linux_env.sh` để đưa vào PATH. Xem [kiểm tra native solver](NATIVE_SOLVERS_CHECK.json). CP Optimizer đã cài từ Studio 22.2, đồng thời đã nối runtime Studio vào Python bằng CLI DOcplex; xem [CPLEX_LINUX.md](CPLEX_LINUX.md) và [CPLEX_CHECK.json](CPLEX_CHECK.json).
- Không sinh dataset v1 hoặc chạy batch chính thức trong quá trình thiết lập.

Chưa xác minh phiên bản Ubuntu/Python của máy chạy ở nhà. Trước batch chính thức phải đối chiếu và cố định Python, dependency, solver, cấu hình và commit trên cả hai máy.
