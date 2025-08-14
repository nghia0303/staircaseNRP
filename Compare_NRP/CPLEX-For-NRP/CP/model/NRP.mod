/*********************************************
 * OPL 22.1.1.0 Model
 * Author: truon
 * Creation Date: May 19, 2025 at 10:48:19 AM
 *********************************************/

using CP;

int nurse = ...; // Number of nurses
int week = ...; // Number of weeks
int msPer28 = ...; // Min shifts per 28 days
int nbDays = week * 7; // Number of days

range Nurses = 1..nurse;
range Days = 1..nbDays;
range Shifts = 0..2;

dvar boolean schedule[Nurses][Days][Shifts];

execute {
    cp.param.ParallelMode = 1; 
    cp.param.Workers = 8;
}

// At most 1 shift per day
constraints {
    forall(n in Nurses, d in Days)
        sum(s in Shifts) schedule[n][d][s] <= 1;
}

// At most 6 shifts per 7 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 6) {
        sum(offset in 0..6, s in Shifts) schedule[n][d + offset][s] <= 6;
    }    
}

// At least 4 dayoffs per 14 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 13) {
        sum(offset in 0..13) (sum(s in Shifts) schedule[n][d + offset][s] == 0 ? 1 : 0) >= 4;
    }    
}

// At least 4 and at most 8 evening shifts per 14 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 13) {
        sum(offset in 0..13) schedule[n][d + offset][1] >= 4;
        sum(offset in 0..13) schedule[n][d + offset][1] <= 8;
    }
}

// At least msPer28 shifts per 28 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 27) {
        sum(offset in 0..27, s in Shifts) schedule[n][d + offset][s] >= msPer28;
    }
}

// At most 2 night shifts per 7 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 6){
        sum(offset in 0..6) schedule[n][d + offset][2] <= 2;
    }
}

// At least 1 night shift per 14 consecutive days
constraints{
    forall(n in Nurses, d in 1..nbDays - 13){
        sum(offset in 0..13) schedule[n][d + offset][2] >= 1;
    }
}

// At least 2 and at most 4 evening or night shifts per 7 consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 6) {
        sum(offset in 0..6) (schedule[n][d+offset][1] + schedule[n][d+offset][2]) >= 2;
        sum(offset in 0..6) (schedule[n][d+offset][1] + schedule[n][d+offset][2]) <= 4;
    }
}

// Two night shifts cannot occur in two consecutive days
constraints {
    forall(n in Nurses, d in 1..nbDays - 1)
        schedule[n][d][2] + schedule[n][d + 1][2] <= 1;
}

execute {
    cp.param.LogPeriod = 0;
    cp.param.LogVerbosity = 0;
}
 