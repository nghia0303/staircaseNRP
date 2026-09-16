# Script sinh sequenceNurse-N — bản chờ duyệt

Ngày: 2026-09-16. **Chỉ chuẩn bị script; chưa sinh bộ dataset ra file. Chờ tác giả kiểm tra script trước khi chạy sinh.**

Script dùng Python 3.10 trở lên và standard library, không cần pypblib, PySAT hoặc solver.
Toàn bộ code cần thiết nằm trong thư mục này và có thể chạy sau khi clone repo staircaseNRP trên máy khác.
Phạm vi là sequenceNurse-N có minimum demand và hard day-off; không thay đổi các method.

## Các file cần xem

| File | Nội dung |
|---|---|
| [generate.py](generate.py) | Tham số CLI, tính demand, dựng lịch tham chiếu, chọn hard day-off và xuất JSON |
| [validate.py](validate.py) | Kiểm tra trực tiếp lịch theo bảy ràng buộc, coverage, hard day-off; kiểm tra manifest/checksum |
| [test_dataset.py](test_dataset.py) | Kiểm thử biên cửa sổ, làm tròn, tái lập seed và phát hiện nghiệm sai |

Trong generate.py, đọc theo thứ tự: allocate_demand → make_reference → choose_off_days → build_instance → main.
Các giá trị dưới đây là **mặc định của bản script để duyệt**, chưa phải một bộ dữ liệu đã được phê duyệt hoặc sinh xong.

## Tham số dự kiến

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| --nurses | 30 40 50 60 70 80 100 120 | Giữ N=70 có trong bảng kết quả cũ |
| --days | 40 60 80 100 112 140 168 | Bốn horizon bản 1 và ba horizon mở rộng đã thảo luận |
| --seeds | 20260916 | Một seed cho mỗi kích thước; tổng dự kiến 56 instance |
| --demand-slack | 0.1 | Giảm 10% từ mốc 5N/7 trước khi làm tròn xuống |
| --shift-weights | 3 5 2 | Phân tổng demand theo D/E/N = 30/50/20 |
| --hard-off-rate | 0.1 | Mỗi y tá có ceil(0.1H) ngày bị ép O |
| --off-phase-count | 2 | Lấy ngày ép nghỉ trong hai lớp dư modulo 14 của lịch tham chiếu |

Mức giảm demand 10% và tỷ lệ hard day-off 10% là hai tham số độc lập.
Ví dụ H=112 có 12 ngày ép nghỉ/y tá, tức khoảng 10.71% sau làm tròn.
Các lưới, seed, mức giảm, tỷ lệ ca và mật độ off đều điều chỉnh được bằng CLI.

## Thuật toán cần duyệt

1. **Giữ đúng bảy ràng buộc Bergman cho mỗi y tá**, mỗi ngày nhận đúng một D/E/N/O. Mọi cửa sổ đầy đủ đều được xét, không nối vòng horizon:

   | Ca được đếm | Cửa sổ | Cận dưới | Cận trên |
   |---|---:|---:|---:|
   | D/E/N | 28 | 20 | 28 |
   | O | 14 | 4 | 14 |
   | N | 14 | 1 | 4 |
   | E | 14 | 4 | 8 |
   | N | 2 | 0 | 1 |
   | E/N | 7 | 2 | 4 |
   | D/E/N | 7 | 0 | 6 |

2. **Tính demand trước khi dựng lịch tham chiếu.** Hai cận work <= 10/14 và work >= 20/28 cùng ép đúng 20 ngày làm việc trong mỗi cửa sổ 28 ngày. Mốc trung bình tương ứng là 5N/7. Tổng demand hằng ngày đặt R = floor((1 - slack) × 5N/7), rồi chia theo trọng số D/E/N. Lấy phần nguyên trước, phân số dư cho ca có phần thập phân lớn nhất; hòa thì ưu tiên D, E, N. Mặc định N=30 cho R=19 và (D,E,N)=(6,9,4). Coverage là actual >= demand, không phải dấu bằng.

   Cơ sở cho trọng số mặc định: trong 28 ngày có đúng 20 ca làm; E>=8, N>=2 và E+N<=16 nên D>=4. Lấy (4,8,2), phân đều 6 ca còn lại cho ba loại, được (6,10,4). **Việc phân đều này là lựa chọn thiết kế**, không phải tỷ lệ bắt buộc trong paper. Khi H không chia hết cho 14, không khẳng định trung bình toàn horizon bằng 5N/7; lập luận trên từng cửa sổ 28 ngày vẫn đúng.

3. **Dựng một lịch tham chiếu đáp ứng demand để có bằng chứng SAT.** Lấy ngẫu nhiên chu kỳ 14 ngày với (D,E,N,O)=(3,5,2,4), giữ chu kỳ thỏa các cửa sổ qua ranh giới khi lặp lại. Mỗi nhóm 14 y tá dùng đủ 14 phép xoay của một chu kỳ, nên đóng góp mỗi ngày đúng (3,5,2,4). Với nhóm y tá dư, xét các tập phép xoay để đáp ứng phần demand còn thiếu. Mỗi nhóm có chu kỳ ngẫu nhiên riêng; cuối cùng hoán vị thứ tự y tá.

   Lịch tham chiếu có chu kỳ chỉ phục vụ việc xây dựng. File instance không ép các ca D/E/N lặp 14 ngày hoặc ép histogram (3,5,2,4). Tuy vậy, **bộ dữ liệu vẫn có thiên lệch do cách xây dựng này**; chứng minh SAT không chứng minh độ khó hoặc tính đại diện.

4. **Chọn hard day-off từ các ô O của lịch tham chiếu.** Với mỗi y tá, chọn ngẫu nhiên hai lớp dư modulo 14 có đủ vị trí; chọn ít nhất một ngày trong mỗi lớp, sau đó lấy đủ ceil(rate × H) ngày không hoàn lại. Đây là lựa chọn cần duyệt: lấy đều trên mọi ô O dễ chạm cả bốn lớp nghỉ, qua cấu trúc chu kỳ có thể cố định toàn bộ mẫu nghỉ. Giới hạn hai lớp giảm việc ép trực tiếp đó; vẫn không bảo đảm benchmark khó. Đây cũng không phải lấy ngẫu nhiên độc lập 10% trên toàn horizon.

5. **Validator riêng kiểm tra nghiệm tham chiếu**, rồi mới ghi instance và nghiệm vào hai thư mục riêng. Lịch tham chiếu không được đưa vào solver hoặc dùng làm warm start khi so sánh method. Không chọn hoặc loại instance theo runtime của Ladder hay method nào khác.

Nếu thay cấu hình vượt khả năng dựng lịch của thuật toán, script báo lỗi. Lỗi dựng lịch **không có nghĩa mô hình UNSAT**. Thay tỷ lệ ca chỉ thay cách phân demand; histogram lịch tham chiếu vẫn là (3,5,2,4), nên script không hứa hỗ trợ mọi tỷ lệ khả thi về mặt toán học.

Demand dương ở nhiều ca cùng ngày loại trường hợp tất cả y tá dùng chung một lịch. Hard day-off không bảo đảm lịch của mọi cặp y tá đều khác nhau.

## Xem cấu hình, chưa sinh dữ liệu

Chạy từ thư mục gốc repo staircaseNRP. Trên Linux dùng python3 như dưới đây; trên Windows có thể thay python3 bằng python hoặc đường dẫn interpreter của môi trường đang dùng:

```bash
python3 -B sequence_nurse_dataset/generate.py --dry-run
```

Lệnh này chỉ in cấu hình, số instance dự kiến, demand theo N và số ngày ép nghỉ theo H. Không dựng lịch tham chiếu, không tạo thư mục hoặc file dataset, không kiểm tra SAT của lưới dự kiến.

## Lệnh sinh sau khi đã duyệt

**Chưa chạy lệnh này trong bước chuẩn bị script.**

```bash
python3 -B sequence_nurse_dataset/generate.py --output datasets/sequence_nurse_v1 --nurses 30 40 50 60 70 80 100 120 --days 40 60 80 100 112 140 168 --seeds 20260916 --demand-slack 0.1 --shift-weights 3 5 2 --hard-off-rate 0.1 --off-phase-count 2 --archive
```

Output phải chưa tồn tại hoặc là thư mục rỗng; script không ghi đè bộ đã có. Nếu sinh lỗi giữa chừng, thư mục có thể chứa kết quả từng phần: chỉ dùng bộ có manifest và validation hoàn tất. Trên Linux thay đường dẫn Python bằng interpreter của môi trường tương ứng.

Các file dự kiến: instances/*.json, reference_solutions/*.json, manifest.json, summary.csv, validation.json, README.md và bản sao hai script trong tools/. Manifest lưu cấu hình, seed, SHA-256 và phiên bản Python. Bộ có thể được tái lập bằng cùng script, cấu hình và môi trường Python; ngày tạo ZIP không được dùng làm định danh nội dung.

Validator có thể chạy riêng sau này:

```bash
python3 -B sequence_nurse_dataset/validate.py --dataset datasets/sequence_nurse_v1
```

Mỗi file nghiệm có schema=nurse-roster-solution-v1, instance_id, status=SAT và schedule gồm N chuỗi dài H trên D/E/N/O. Validator kiểm tra nghiệm SAT, không chứng minh UNSAT. Trong instance, hard_day_off[n-1] liệt kê ngày từ 1 và demand[d-1] là nhu cầu ca của ngày d.

## Nguồn và trạng thái

- Bảy ràng buộc: Bergman et al. (2014), MDD Propagation for Sequence Constraints, Table 1, trang in 717. Bảng đầy đủ đã được chép ở trên để thư mục có thể chuyển sang máy khác độc lập với các ghi chú ngoài repo.
- Cận 5N/7: lập luận từ hai cận 10/14 và 20/28 được ghi ở bước 2 phía trên. Script cụ thể hóa phương án giảm từ mốc trung bình; phương án dùng trực tiếp ngân sách cửa sổ 14/28 ngày vẫn là hướng riêng chưa triển khai.
- Các bộ test trong bộ nhớ đã chạy trước yêu cầu dừng sinh. Chưa sinh dataset ra file, chưa chạy benchmark hoặc đo hiệu năng method.
