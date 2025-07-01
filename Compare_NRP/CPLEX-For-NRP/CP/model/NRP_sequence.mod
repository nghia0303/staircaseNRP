using CP;
int nurse = ...;
int week = ...;
int nbDays = week * 7;
range Nurses = 1..nurse;
range Days = 1..nbDays;
int NightShift = 2;

dvar interval schedule[Nurses][Days][0..2] optional size 1;

subject to {
  // Tối đa 1 ca/ngày
  forall(n in Nurses, d in Days)
    sum(s in 0..2) presenceOf(schedule[n][d][s]) <= 1;

  // At most 2 night shifts in any 7 consecutive days (using IloSequence)
  forall(n in Nurses, d in 1..nbDays-6)
    sequence([schedule[n][dd][NightShift] | dd in d..d+6], 7, 0, 2);
        }

// Giải mô hình
execute {
  cp.param.Workers = 8;
}
