# Picat và MiniCPP/HADDOCK trên Linux

Cập nhật 2026-09-21. Cài đặt dành cho Linux x86_64; môi trường đã kiểm tra là WSL Ubuntu-26.04.

## Cài và gọi chương trình

Sau khi cài các gói apt trong [WSL_ENVIRONMENT.md](WSL_ENVIRONMENT.md), từ gốc repo:

```bash
bash scripts/setup_native_linux.sh
source scripts/linux_env.sh
python -B scripts/check_native_solvers.py --output tmp/native-solvers-check.json
```

Script cài dùng Python Linux >=3.12, curl, git, CMake, GCC và make. Không cần pip package Picat. Nó tải executable chính thức Picat, kiểm tra SHA256; lấy source MiniCPP đã ghim, áp dụng hai patch trong repo rồi build ba executable. Mặc định build hai luồng; có thể đặt `NRP_BUILD_JOBS=4` nếu máy đủ RAM.

Mặc định cài tại `$HOME/.local/opt/sequenceconstraint`; có thể đổi bằng `NRP_NATIVE_HOME` và phải dùng cùng giá trị khi setup, source môi trường và kiểm tra. Cache tải xuống ở `$HOME/.cache/sequenceconstraint/native`. Không đưa binary, cache hoặc virtualenv lên Git.

Sau `source scripts/linux_env.sh`, dùng được `picat`, `amongNurse`, `sequenceNurse` và `sequenceNurseNew` qua PATH. File này cũng đặt các biến đường dẫn mà ba script batch cũ sử dụng. Không cần sửa đường dẫn `/home/nghia` trên máy Ubuntu khác. Source lại file này khi mở terminal mới; không tự sửa shell profile của người dùng.

Ví dụ kiểm tra riêng Picat trên NRP-2010:

```bash
picat "$SRC_PATH/Compare_NRP_2010/Picat/sample.pi" 2 40 0
```

Kết quả mong đợi `solns : 3`; đổi đối số cuối thành `1` để tìm một nghiệm. Picat hiện tại chấp nhận cú pháp `if` trong file này; không sửa model NRP-2010 khi cài runtime.

## Phiên bản và bằng chứng

- Picat **3.9#12**, từ [trang tải chính thức](https://picat-lang.org/download.html), phát hành 2026-08-28. SHA256 archive được ghim trong script là checksum của file đã tải; không phải chữ ký số của nhà phát hành.
- MiniCPP Bitbucket master **9bf9110059c1e883efbc97d79640486c1cd5d8b2**, kèm frontend hiện có của dự án và hai khởi tạo Boolean rõ ràng. Chi tiết và giới hạn ở [native/minicpp/README.md](../native/minicpp/README.md).
- C++17, Release, GCC 15.2.0 trên máy WSL này. Compiler ở máy Ubuntu khác có thể khác; phải đối chiếu manifest trước batch chính thức.
- `$NRP_NATIVE_HOME/manifest.json` ghi nguồn, commit, checksum patch và binary, compiler, đường dẫn build log. Manifest thay đổi theo binary thực tế của từng máy.
- [NATIVE_SOLVERS_CHECK.json](NATIVE_SOLVERS_CHECK.json) lưu kết quả kiểm tra local, lệnh gọi, stdout và log runlim; đây là kiểm tra chức năng, không phải kết quả hiệu năng dùng trong paper.

NRP-2010: Picat và MiniCPP mode 0/1/2 đều được kiểm tra hai chế độ (đếm hết: 3 nghiệm; tìm đầu tiên: 1 nghiệm) ở C-II/H=40. Số đếm 3 đã được đối chiếu với Ladder và DE trong [WSL_ENVIRONMENT_CHECK.json](WSL_ENVIRONMENT_CHECK.json). Sequence: kiểm tra N=1/H=28 với sequenceNurse mode 0/2 và sequenceNurseNew mode 4. Không sinh dataset hoặc chạy batch chính thức.

## Việc vẫn thuộc bước kiểm tra method

Executable Picat và bước build MiniCPP/HADDOCK đã có quy trình cài lại. CP Optimizer cũng đã được cài bổ sung từ bộ Studio 22.2 người dùng cung cấp; xem [CPLEX_LINUX.md](CPLEX_LINUX.md). Điều này không chứng nhận toàn bộ tám method: các model Sequence-N cũ còn cần sửa/kiểm tra ràng buộc, vòng nurse và tham số trước khi chạy phiên bản có shift-off/demand. Batch shell cũ vẫn giữ logic lịch sử; không coi nó là runner mới 300 giây đã thống nhất.
