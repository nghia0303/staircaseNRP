using CP;

int days = 40; // Number of days

int classType = 1; // Number of class types

range Days = 1..days;
dvar boolean x[Days];

int ub[3] = [6, 6, 7];
int ubWindow[3] = [8, 9, 9];
int lb[3] = [22, 20, 22];
int lbWindow[3] = [30, 30, 30];

execute {
    cp.param.ParallelMode = 1;
    cp.param.Workers = 8;
}

execute {
        writeln("Solution: ", x);
}

