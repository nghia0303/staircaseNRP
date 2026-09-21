# Môi trường phát triển và thực nghiệm

- Dự án dùng Linux: WSL 2 trên máy Windows để code/debug/kiểm tra; máy Ubuntu riêng ở nhà để chạy thực nghiệm chính thức sau khi pull Git.
- Đọc [docs/WSL_ENVIRONMENT.md](docs/WSL_ENVIRONMENT.md) để biết interpreter, dependency, bước kiểm tra và các thành phần chưa cài.
- Picat/MiniCPP-HADDOCK: đọc [docs/NATIVE_SOLVERS.md](docs/NATIVE_SOLVERS.md); cài bằng `bash scripts/setup_native_linux.sh`, dùng `source scripts/linux_env.sh`. MiniCPP ghim commit Bitbucket và hai patch trong `native/minicpp`; không lấy binary cũ trong thư mục MiniCP bị gitignore. Cài executable không thay thế audit model Sequence-N; các lỗi model cũ được ghi trong tài liệu native.
- CP Optimizer và CPLEX Studio 22.2 đã cài trong WSL: xem [docs/CPLEX_LINUX.md](docs/CPLEX_LINUX.md). Sau khi thay/cài lại wheel cplex, phải nối lại runtime Studio bằng `docplex config --upgrade` và kiểm tra; metadata pip không thay thế phiên bản/checksum engine thực dùng. Bộ cài Windows chưa cài trong bước WSL này.
- Không dùng virtualenv Windows trong WSL. Không hard-code đường dẫn /home/nghia trong logic các method; các đường dẫn máy cụ thể thuộc hướng dẫn hoặc cấu hình môi trường.
- Không tự chạy sinh dataset sequenceNurse-N v1 hoặc batch chính thức trong bước cài môi trường. Không thay đổi semantics liệt kê nghiệm khi chưa có yêu cầu triển khai.
- Giữ nguyên các thay đổi chưa commit không thuộc nhiệm vụ. Không commit virtualenv, cache, license hoặc credential.
