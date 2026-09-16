"""Generate capacity-based sequenceNurse-N instances using only Python stdlib."""

from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path
import platform
import random
import shutil
import sys

from validate import validate_solution, validate_dataset


VERSION = "v1"
DEFAULT_NURSES = [30, 40, 50, 60, 70, 80, 100, 120]
DEFAULT_DAYS = [40, 60, 80, 100, 112, 140, 168]
SHIFTS = ["D", "E", "N", "O"]
REFERENCE_COUNTS = {"D": 3, "E": 5, "N": 2, "O": 4}


def check_parameters(nurses, days, slack, weights, off_rate, off_phases):
    """Check configuration only; do not construct a reference or write files."""
    if nurses < 2 or days < 28:
        raise ValueError("This generator targets N>=2, H>=28")
    if not 0 <= slack < 1 or not 0 <= off_rate <= 1:
        raise ValueError("Expected 0<=demand-slack<1 and 0<=hard-off-rate<=1")
    if len(weights) != 3 or any(w <= 0 for w in weights) or not 1 <= off_phases <= 4:
        raise ValueError("Positive D/E/N weights and 1..4 off phases are required")
    if sum(v > 0 for v in allocate_demand(nurses, slack, weights).values()) < 2:
        raise ValueError("Require positive demand on at least two working shifts")
    count = hard_off_count(days, off_rate)
    # This upper bound does not depend on a generated reference.
    phase_days = sorted((len(range(p, days, 14)) for p in range(14)), reverse=True)
    if count > sum(phase_days[:off_phases]):
        raise ValueError("Hard-off rate exceeds the capacity of the selected residue classes")


def hard_off_count(days, rate):
    fraction = rate * days
    return -(-fraction.numerator // fraction.denominator)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_json(path, value):
    path.write_text(json_text(value), encoding="utf-8", newline="\n")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_seed(seed, nurses, days):
    label = f"{VERSION}|{seed}|{nurses}|{days}"
    return int.from_bytes(hashlib.sha256(label.encode("ascii")).digest()[:8], "big")


def allocate_demand(nurses, slack, weights):
    total = int((1 - slack) * Fraction(5 * nurses, 7))
    quotas = [Fraction(total * w, sum(weights)) for w in weights]
    counts = [q.numerator // q.denominator for q in quotas]
    order = sorted(range(3), key=lambda i: (-(quotas[i] - counts[i]), i))
    for i in order[:total - sum(counts)]:
        counts[i] += 1
    return dict(zip(SHIFTS[:3], counts))


def valid_cycle(cycle):
    for start in range(14):
        week = [cycle[(start + i) % 14] for i in range(7)]
        if not 2 <= sum(s in "EN" for s in week) <= 4:
            return False
        if sum(s != "O" for s in week) > 6:
            return False
        if cycle[start] == cycle[(start + 1) % 14] == "N":
            return False
    return True


def sample_cycle(rng):
    cycle = list("DDD" + "EEEEE" + "NN" + "OOOO")
    for attempt in range(1, 100001):
        rng.shuffle(cycle)
        if valid_cycle(cycle):
            return "".join(cycle), attempt
    raise RuntimeError("Reference-cycle construction exhausted; this is not an UNSAT result")


def extend_cycle(cycle, phase, days):
    return "".join(cycle[(day + phase) % 14] for day in range(days))


def make_reference(nurses, days, demand, rng):
    """Use balanced groups of 14 rotations; no restriction is added to the instance."""
    groups, remainder = divmod(nurses, 14)
    schedules, trials = [], 0
    for _ in range(groups):
        cycle, attempts = sample_cycle(rng)
        trials += attempts
        schedules.extend(extend_cycle(cycle, phase, days) for phase in range(14))
    deficits = {s: max(0, demand[s] - groups * REFERENCE_COUNTS[s]) for s in SHIFTS[:3]}
    if not remainder and any(deficits.values()):
        raise ValueError("The reference construction cannot cover this demand; not an UNSAT result")
    if remainder:
        for _ in range(128):
            cycle, attempts = sample_cycle(rng)
            trials += attempts
            phase_sets = list(combinations(range(14), remainder))
            rng.shuffle(phase_sets)
            chosen = None
            for phases in phase_sets:
                if all(sum(cycle[(day + p) % 14] == s for p in phases) >= needed
                       for day in range(14) for s, needed in deficits.items() if needed):
                    chosen = phases
                    break
            if chosen is not None:
                schedules.extend(extend_cycle(cycle, phase, days) for phase in chosen)
                break
        else:
            raise ValueError("No residual reference group found; not an UNSAT result")
    rng.shuffle(schedules)
    return schedules, trials


def choose_off_days(row, count, phase_count, rng):
    if count == 0:
        return []
    phases_needed = min(count, phase_count)
    off_phases = [i for i in range(14) if row[i] == "O"]
    eligible = []
    for phases in combinations(off_phases, phases_needed):
        days = [d for d in range(1, len(row) + 1) if (d - 1) % 14 in phases]
        if len(days) >= count:
            eligible.append((phases, days))
    if not eligible:
        raise ValueError("Hard-off rate does not fit the configured number of residue classes")
    phases, available = rng.choice(eligible)
    chosen = [rng.choice([d for d in available if (d - 1) % 14 == p]) for p in phases]
    remaining = [d for d in available if d not in chosen]
    chosen.extend(rng.sample(remaining, count - len(chosen)))
    return sorted(chosen)


def build_instance(nurses, days, seed, slack=Fraction(1, 10),
                   weights=(3, 5, 2), off_rate=Fraction(1, 10), off_phases=2):
    check_parameters(nurses, days, slack, weights, off_rate, off_phases)
    demand = allocate_demand(nurses, slack, weights)
    instance_seed = derive_seed(seed, nurses, days)
    rng = random.Random(instance_seed)
    reference, cycle_trials = make_reference(nurses, days, demand, rng)
    off_count = hard_off_count(days, off_rate)
    hard_off = [choose_off_days(row, off_count, off_phases, rng) for row in reference]
    identifier = f"sequence_nurse_n{nurses:03d}_h{days:03d}_s{seed}"
    rules = [
        (["D", "E", "N"], 28, 20, 28),
        (["O"], 14, 4, 14),
        (["N"], 14, 1, 4),
        (["E"], 14, 4, 8),
        (["N"], 2, 0, 1),
        (["E", "N"], 7, 2, 4),
        (["D", "E", "N"], 7, 0, 6),
    ]
    instance = {
        "schema": "sequence-nurse-instance-v1",
        "instance_id": identifier,
        "problem": "sequenceNurse-N",
        "nurses": nurses, "days": days, "shifts": SHIFTS, "index_base": 1,
        "assignment_semantics": "exactly_one_shift_per_nurse_per_day",
        "window_semantics": "all_full_windows_no_wrap",
        "sequence_constraints": [{"shifts": s, "window": q, "lower": l, "upper": u}
                                 for s, q, l, u in rules],
        "coverage_semantics": "minimum_per_day_per_working_shift",
        "demand": [dict(demand) for _ in range(days)],
        "hard_day_off": hard_off,
        "generation": {
            "version": VERSION, "seed": seed, "instance_seed": instance_seed,
            "demand_slack": str(slack), "shift_weights": list(weights),
            "daily_total_demand": sum(demand.values()),
            "demand_rounding": "floor_total_then_largest_remainders",
            "remainder_tie_order": ["D", "E", "N"],
            "hard_off_rate": str(off_rate), "hard_off_count_per_nurse": off_count,
            "off_count_rounding": "ceil(rate * H)",
            "off_phase_count": off_phases,
            "off_sampling": "choose_eligible_residue_subset_then_one_day_per_residue_then_remaining_days",
            "reference_construction": "balanced_rotations_of_random_feasible_14_day_cycles",
            "reference_cycle_counts": REFERENCE_COUNTS,
            "reference_cycle_shuffle_attempts": cycle_trials,
            "selection_by_solver_runtime": False,
        },
    }
    solution = {
        "schema": "nurse-roster-solution-v1",
        "instance_id": identifier, "status": "SAT",
        "provenance": "constructive_reference_not_a_solver_run",
        "schedule": reference,
    }
    report = validate_solution(instance, solution)
    if not report["valid"]:
        raise RuntimeError(f"Independent validation failed: {report['errors']}")
    return instance, solution, report


def dataset_readme(config, count):
    return f"""# sequenceNurse-N: {VERSION}

Bộ dữ liệu được sinh theo phương án demand từ hai cận làm việc.
Đây là bộ đầu tiên để kiểm tra tích hợp và chạy thử; chưa có kết quả so sánh hiệu năng.

- Số instance: {count}; mỗi kích thước có {len(config['seeds'])} seed.
- N: {config['nurses']}.
- H: {config['days']}.
- Seed: {config['seeds']}.
- Demand mỗi ngày: floor((1 - {config['demand_slack']}) * 5N/7).
- Tỷ lệ D/E/N: {config['shift_weights']}; làm tròn phần dư lớn nhất, hòa theo D,E,N.
- Hard day-off mỗi y tá: ceil({config['hard_off_rate']} * H); lấy trong {config['off_phase_count']} lớp ngày modulo 14.

## File và semantics

instances/*.json là dữ liệu đầu vào cho các method. manifest.json liệt kê đầy đủ
đường dẫn, SHA-256, kích thước và demand. summary.csv tiện xem nhanh.
reference_solutions/*.json là lịch tham chiếu riêng để kiểm tra SAT.
Không cấp lịch tham chiếu cho solver, không dùng làm warm start trong benchmark.
validation.json là báo cáo validator độc lập trên tất cả lịch tham chiếu.

Trong instance, nurse và day tính từ 1; thứ tự ca là D,E,N,O.
hard_day_off[n-1] là danh sách ngày ép y tá n nhận O.
demand[d-1] có ba số nguyên D,E,N: số người tối thiểu cho ngày d, không phải số chính xác.
Mỗi ô nurse/day nhận đúng một ca. Bảy constraint áp dụng mọi cửa sổ đầy đủ,
không nối vòng cuối horizon về đầu. Không thêm objective, preference hoặc nghỉ 12 giờ.

## Cách sinh và giới hạn diễn giải

Hai cận work<=10/14 và work>=20/28 ép đúng 20 lượt làm việc/y tá trong mỗi
cửa sổ 28 ngày. Do đó 5N/7 là mốc capacity trung bình trên cửa sổ đó.
Với H không chia hết cho 14, không khẳng định trung bình toàn horizon đúng bằng 5N/7.

Trong 28 ngày, E>=8, N>=2; E+N<=16 và tổng work=20 cho D>=4.
Phân đều 6 ca còn lại vào (4,8,2) cho tỷ lệ tham chiếu mặc định (6,10,4), tức 30/50/20.
Việc phân đều là lựa chọn thiết kế, không phải tỷ lệ bắt buộc của Bergman.
Ở cấu hình mặc định (slack=0.1, weights=3/5/2), N=30 có demand D/E/N=6/9/4.
Tham số thực tế của bộ này nằm ở đầu README và trong manifest.json.

Demand được tính trước khi dựng lịch tham chiếu. Để có bằng chứng khả thi,
generator tạo các chu kỳ 14 ngày với (D,E,N,O)=(3,5,2,4), kiểm tra các cửa sổ
qua ranh giới chu kỳ, rồi ghép từng nhóm 14 phép xoay. Nhóm dư được chọn để đáp ứng
demand đã tính. Chu kỳ được lấy bằng hoán vị ngẫu nhiên có seed, nurse được hoán vị.
Lịch tham chiếu lặp 14 ngày là công cụ xây dựng; instance KHÔNG ép D/E/N lặp chu kỳ,
không ép số D/E/N bằng histogram của lịch tham chiếu.

Hard day-off lấy từ các ô O của lịch tham chiếu. Chọn đều một tập lớp dư đủ chỗ,
chọn một ngày ngẫu nhiên trong mỗi lớp rồi lấy đủ các ngày còn lại không hoàn lại.
Giới hạn mặc định hai lớp dư tránh trực tiếp ép cả bốn lớp O, nhưng không chứng minh mọi
lịch còn nhiều lựa chọn hoặc benchmark khó. Đây là dữ liệu tổng hợp có nghiệm
tham chiếu; phân bố chịu ảnh hưởng cấu trúc chu kỳ và cách chọn off.
Không lọc/chọn instance theo thời gian Ladder hay theo chênh lệch giữa các method.

## Sinh lại và validate

Generator và validator dùng Python standard library, không cần pypblib/PySAT.
Bản sao hai script và checksum được lưu trong tools/ và manifest.
Chạy từ thư mục dataset:

    python tools/generate.py --output ../regenerated --nurses {' '.join(map(str, config['nurses']))} --days {' '.join(map(str, config['days']))} --seeds {' '.join(map(str, config['seeds']))} --demand-slack {config['demand_slack']} --shift-weights {' '.join(map(str, config['shift_weights']))} --hard-off-rate {config['hard_off_rate']} --off-phase-count {config['off_phase_count']}
    python tools/validate.py --dataset . --output validation.json

Thư mục output mới phải chưa tồn tại hoặc rỗng; generator không ghi đè bộ đã có.
Đầu ra solver chuẩn cho validator: schema=nurse-roster-solution-v1, instance_id,
status=SAT, schedule là N chuỗi dài H trên alphabet D/E/N/O.
Validator kiểm tra từng cửa sổ trực tiếp, coverage, hard-off, công thức demand và checksum.
Validator này kiểm tra nghiệm SAT, không chứng minh UNSAT hoặc đầy đủ enumeration.

## Nguồn

Bảy constraint: Bergman et al. (2014), Table 1, trang in 717 / PDF trang 21.
Demand và hard-off là mở rộng của tác giả, không phải dữ liệu gốc Bergman/NSPLib.
Lưới mặc định giữ N=70 vì có trong bảng kết quả cũ; H mặc định dùng bốn mốc
40/60/80/100 và ba mốc mở rộng 112/140/168 theo trao đổi. Lưới thực tế nằm trong manifest.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--output", type=Path, help="New dataset directory; required except for --dry-run")
    parser.add_argument("--nurses", type=int, nargs="+", default=DEFAULT_NURSES,
                        help="Numbers of nurses")
    parser.add_argument("--days", type=int, nargs="+", default=DEFAULT_DAYS,
                        help="Horizon lengths")
    parser.add_argument("--seeds", type=int, nargs="+", default=[20260916],
                        help="Independent generation seeds")
    parser.add_argument("--demand-slack", type=Fraction, default=Fraction(1, 10),
                        help="Fraction removed from 5N/7; accepts 0.1 or 1/10")
    parser.add_argument("--shift-weights", type=int, nargs=3, default=[3, 5, 2],
                        metavar=("D", "E", "N"), help="Positive demand weights in D/E/N order")
    parser.add_argument("--hard-off-rate", type=Fraction, default=Fraction(1, 10),
                        help="Hard off days per nurse: ceil(rate * H)")
    parser.add_argument("--off-phase-count", type=int, default=2,
                        help="Number of off residue classes modulo 14 to sample (1..4)")
    parser.add_argument("--archive", action="store_true", help="Also create a ZIP archive")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print configuration and demand only; no roster construction or file writes")
    args = parser.parse_args()
    config = {
        "nurses": sorted(set(args.nurses)), "days": sorted(set(args.days)),
        "seeds": sorted(set(args.seeds)), "demand_slack": str(args.demand_slack),
        "shift_weights": args.shift_weights, "hard_off_rate": str(args.hard_off_rate),
        "off_phase_count": args.off_phase_count,
    }
    try:
        for nurses in config["nurses"]:
            for days in config["days"]:
                check_parameters(nurses, days, args.demand_slack, args.shift_weights,
                                 args.hard_off_rate, args.off_phase_count)
    except ValueError as exc:
        parser.error(str(exc))
    if args.dry_run:
        preview = {
            "mode": "dry_run_no_generation", "configuration": config,
            "planned_instances": len(config["nurses"]) * len(config["days"]) * len(config["seeds"]),
            "demand_by_nurses": {str(n): allocate_demand(n, args.demand_slack, args.shift_weights)
                                  for n in config["nurses"]},
            "hard_off_per_nurse_by_days": {str(h): hard_off_count(h, args.hard_off_rate)
                                            for h in config["days"]},
            "feasibility": "not_checked_in_dry_run",
        }
        print(json_text(preview), end="")
        return 0
    if args.output is None:
        parser.error("--output is required unless --dry-run is used")
    root = args.output.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        parser.error(f"Output is not an empty directory: {root}")
    archive_path = Path(str(root) + ".zip")
    if args.archive and archive_path.exists():
        parser.error(f"Archive already exists: {archive_path}")
    for directory in ["instances", "reference_solutions", "tools"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    source_dir = Path(__file__).resolve().parent
    for filename in ["generate.py", "validate.py"]:
        shutil.copyfile(source_dir / filename, root / "tools" / filename)
    entries, summaries = [], []
    for seed in config["seeds"]:
        for nurses in config["nurses"]:
            for days in config["days"]:
                instance, solution, report = build_instance(
                    nurses, days, seed, args.demand_slack, tuple(args.shift_weights),
                    args.hard_off_rate, args.off_phase_count)
                identifier = instance["instance_id"]
                instance_relative = f"instances/{identifier}.json"
                solution_relative = f"reference_solutions/{identifier}.json"
                write_json(root / instance_relative, instance)
                write_json(root / solution_relative, solution)
                demand = instance["demand"][0]
                entry = {
                    "instance_id": identifier, "nurses": nurses, "days": days, "seed": seed,
                    "demand_per_day": demand, "total_demand_per_day": sum(demand.values()),
                    "hard_off_per_nurse": instance["generation"]["hard_off_count_per_nurse"],
                    "instance_path": instance_relative,
                    "instance_sha256": file_hash(root / instance_relative),
                    "reference_solution_path": solution_relative,
                    "reference_solution_sha256": file_hash(root / solution_relative),
                    "feasibility": "SAT_by_independently_validated_reference",
                }
                entries.append(entry)
                summaries.append({
                    "instance_id": identifier, "nurses": nurses, "days": days, "seed": seed,
                    "demand_D": demand["D"], "demand_E": demand["E"], "demand_N": demand["N"],
                    "total_demand_per_day": sum(demand.values()),
                    "demand_capacity_ratio": round(sum(demand.values()) * 7 / (5 * nurses), 8),
                    "hard_off_per_nurse": entry["hard_off_per_nurse"],
                    "hard_off_density": round(entry["hard_off_per_nurse"] / days, 8),
                    "forced_off_residues": report["hard_off_residues_max"],
                    "actual_work_daily_min": report["actual_work_daily_min"],
                    "actual_work_daily_max": report["actual_work_daily_max"],
                    "distinct_reference_schedules": report["distinct_reference_schedules"],
                    "feasibility": entry["feasibility"],
                    "instance_path": instance_relative,
                })
                print(f"Generated {len(entries)}: N={nurses} H={days} demand={demand} validated", flush=True)
    manifest = {
        "schema": "sequence-nurse-manifest-v1", "generator_version": VERSION,
        "configuration": config, "instance_count": len(entries),
        "python_version": platform.python_version(),
        "tool_sha256": {f"tools/{name}": file_hash(root / "tools" / name)
                       for name in ["generate.py", "validate.py"]},
        "instances": entries,
    }
    write_json(root / "manifest.json", manifest)
    with (root / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    (root / "README.md").write_text(dataset_readme(config, len(entries)), encoding="utf-8", newline="\n")
    report = validate_dataset(root)
    write_json(root / "validation.json", report)
    if not report["valid"]:
        raise RuntimeError("Final dataset validation failed; see validation.json")
    if args.archive:
        shutil.make_archive(str(root), "zip", root_dir=root.parent, base_dir=root.name)
    print(json.dumps({"output": str(root), "instances": len(entries), "all_valid": report["valid"],
                      "archive": str(archive_path) if args.archive else None}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
