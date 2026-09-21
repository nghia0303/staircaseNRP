# CPLEX Optimization Studio trong WSL

Bộ cài người dùng cung cấp: `IBM_ILOG_CPLEX_OptStdv22.2_LIN.bin` trong `C:\Users\ADMIN\DownloadDirector`. Bản Windows cũng có trong thư mục này, nhưng môi trường thực nghiệm hiện dùng **bản Linux trong WSL**.

## Cài lại trên máy Ubuntu

Chuyển bộ cài Linux bằng kênh riêng sang máy đích; không đưa installer hoặc thông tin license lên Git. Từ gốc repo:

```bash
sudo apt-get install -y --no-install-recommends openjdk-21-jre-headless
bash scripts/setup_linux.sh
bash scripts/setup_cplex_linux.sh /path/to/IBM_ILOG_CPLEX_OptStdv22.2_LIN.bin
source scripts/linux_env.sh
runlim -r 60 -s 2048 python -B scripts/check_cplex_linux.py --output tmp/cplex-check.json
```

Script thực hiện cài silent và chấp nhận license đi kèm theo yêu cầu cài đặt. Cơ chế response file dựa trên [hướng dẫn IBM](https://www.ibm.com/docs/en/icos/22.1.1?topic=2211-silent-installation-cplex-optimization-studio); cấu hình đã được chạy thực tế với installer 22.2 do người dùng cung cấp. Java đi kèm không khởi động được trong WSL này; cài OpenJDK 21 và truyền rõ `LAX_VM` đã giải quyết bước chạy installer.

Mặc định: `$HOME/.local/opt/ibm/ILOG/CPLEX_Studio2220`. Có thể đặt `CPLEX_STUDIO_DIR` khi setup và source môi trường. Script từ chối ghi đè thư mục đã có. Log installer và SHA256 bộ cài nằm ở `$HOME/.cache/sequenceconstraint/cplex-install`.

## Nối với Python

`source scripts/linux_env.sh` đưa `cpoptimizer` và `cplex` vào PATH, đồng thời đặt `CPO_EXECUTABLE`. Hai model CP hiện có đã bỏ đường dẫn cứng 22.1.1 và dùng biến này, hoặc tìm `cpoptimizer` trên PATH.

Đã chạy lệnh chính thức của CLI DOcplex:

```bash
"$NRP_VENV/bin/docplex" config --upgrade "$CPLEX_STUDIO_DIR"
```

Lệnh này chép runtime CPLEX từ bản Studio vào môi trường Python và chép executable CP Optimizer vào `venv/bin`. Đây là bước riêng ngoài `pip install cplex/docplex`. **Nếu cài lại/nâng package `cplex`, chạy lại lệnh config trên và kiểm tra**, vì pip có thể thay runtime Studio bằng runtime đóng gói trong wheel. Phiên bản package và phiên bản engine phải ghi riêng; checksum thư viện thực dùng được lưu trong report.

## Kiểm tra

[CPLEX_CHECK.json](CPLEX_CHECK.json) ghi kết quả thực tế và phiên bản engine. Cả ba kiểm tra đã qua: model CP và MP có 1.100 biến nhị phân (tổng bằng 550), cùng model NRP-2010 C-II/H=40 đếm đúng 3 nghiệm. Các nghiệm nurse được kiểm tra cửa sổ và tuần lịch trực tiếp sau khi solver trả về. Test NRP sử dụng Auto và một worker; không đổi cấu hình search của code benchmark. Lần thử ban đầu với DepthFirst/15 giây không tìm được nghiệm; Auto/30 giây đã liệt kê đủ 3 nghiệm. Không diễn giải lần dừng sớm là UNSAT.

Engine CPLEX từ bộ Studio này báo **22.2.0.0**; metadata pip vẫn ghi package `cplex==22.2.0.1`. Đây là hai thông tin riêng: `docplex config --upgrade` đã thay thư viện native trong wheel bằng bản Studio. SHA256 thư viện thực dùng nằm trong report; không gọi engine này là 22.2.0.1 chỉ dựa vào pip.

Đây là kiểm tra khả năng chạy và phát hiện giới hạn kích thước nhỏ, không phải chứng nhận quyền sử dụng license hoặc hiệu năng trên toàn bộ dataset. Bản Windows chưa cài trong bước thiết lập WSL này.
