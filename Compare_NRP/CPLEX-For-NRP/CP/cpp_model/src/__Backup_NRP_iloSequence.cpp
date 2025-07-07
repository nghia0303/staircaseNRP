#include <ilcp/cp.h>
#include <iostream>
#include <vector>
#include <cstdlib> // std::atoi

using namespace std;

int main(int argc, char** argv) {
    IloEnv env;
    try {
        // ---------------------- Thiết lập mô hình ----------------------
        IloModel model(env);

       if (argc < 4) {
            std::cerr << "Usage: " << argv[0] << " <nurse> <week> <msPer28>\n";
            return 1;
        }
        int nurse   = std::atoi(argv[1]);
        int week    = std::atoi(argv[2]);
        int msPer28 = std::atoi(argv[3]);
        
        cout << "Nurse: " << nurse << ", Week: " << week << ", msPer28: " << msPer28 << std::endl;

        int nbDays  = week * 7;

        // Tạo mảng 3 chiều schedule[n][d][s] với domain 0..1
        // Dùng 1D Flatten: schedule[n][d][s] = schedule[n*nbDays*3 + d*3 + s]
        IloIntVarArray schedule(env, nurse * nbDays * 3, 0, 1);

        auto idx = [&](int n, int d, int s) {
            return n * nbDays * 3 + d * 3 + s;
        };

        // ---------------------- Ràng buộc ----------------------

        // At most 1 shift per day
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d < nbDays; d++){
                IloExpr sum(env);
                for(int s = 0; s < 3; s++){
                    sum += schedule[idx(n,d,s)];
                }
                model.add(sum <= 1);
                sum.end();
            }
        }

        // Sequence constraints
        IloIntArray    workingShiftVal(env, 1, 1); 
        IloIntArray    dayoffVal(env, 1, 0); // Day off = 0
         // Không dùng cards, chỉ cần values
        
    
        for(int n = 0; n < nurse; n++){
            IloIntVarArray varOfThisNurse(env);
            for(int d = 0; d < nbDays; d++){
                for (int s = 0; s < 3; s++){
                    varOfThisNurse.add(schedule[idx(n, d, s)]);
                }
            }
            IloIntVarArray emptyCards(env, 1, 0, varOfThisNurse.getSize());
           
            // At most 6 shifts per 7 consecutive days
            model.add(IloSequence(
                env,
                0, // nbMin,
                6, // nbMax,
                7, // seqWidth
                varOfThisNurse,
                workingShiftVal, // 1
                emptyCards // cards (not used)
            ));

            // At least 4 dayoffs per 14 consecutive days
            model.add(IloSequence(
                env,
                4, // nbMin,
                14, // nbMax (không giới hạn)
                14, // seqWidth
                varOfThisNurse,
                dayoffVal, // dayoffVal = 0
                emptyCards // cards (not used)
            ));


            // At least 4 and at most 8 evening shifts per 14 consecutive days
            IloIntVarArray eveningShifts(env);
            IloIntVarArray nightShifts(env);
            for(int d = 0; d < nbDays; d++){
                eveningShifts.add(schedule[idx(n, d, 1)]); // Evening shift = 1
                nightShifts.add(schedule[idx(n, d, 2)]); // Night shift = 2
            }
            model.add(IloSequence(
                env,
                4, // nbMin,
                8, // nbMax,
                14, // seqWidth
                eveningShifts,
                workingShiftVal, // 1
                emptyCards // cards (not used)
            ));

            // At least msPer28 shifts per 28 consecutive days
            // model.add(IloSequence(
            //     env,
            //     msPer28, // nbMin
            //     28, // nbMax (không giới hạn)
            //     28, // seqWidth
            //     varOfThisNurse,
            //     workingShiftVal, // 1
            //     emptyCards // cards (not used)
            // ));

            // 2-4 evening or night shifts (s=1 or s=2) per 7 days
            // IloIntVarArray eveningOrNightShifts(env);
            // for(int d = 0; d < nbDays; d++){
            //     eveningOrNightShifts.add(schedule[idx(n, d, 1)]); 
            //     eveningOrNightShifts.add(schedule[idx(n, d, 2)]);
            // }

            // model.add(IloSequence(
            //     env,
            //     2, // nbMin
            //     4, // nbMax
            //     7, // seqWidth
            //     eveningOrNightShifts,
            //     workingShiftVal, // 1
            //     emptyCards // cards (not used)
            // ));

            // // At least 1 night shift per 14 consecutive days
            // model.add(IloSequence(
            //     env,
            //     1, // nbMin
            //     14, // nbMax (không giới hạn)
            //     14, // seqWidth
            //     nightShifts,
            //     workingShiftVal, // dayoffVal = 0
            //     emptyCards // cards (not used)
            // ));
                

        }

        

        // Two night shifts is not possible on consecutive days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d < nbDays - 1; d++){
                model.add(schedule[idx(n,d,2)] + schedule[idx(n,d+1,2)] <= 1);
            }
        }

        // ---------------------- Giải bài toán ----------------------
        IloCP cp(model);
        cp.setParameter(IloCP::LogVerbosity, IloCP::Terse);
        if (cp.solve()) {
            std::cout << "Nurse scheduling:" << std::endl;
            for(int n = 0; n < nurse; n++){
                std::cout << "Nurse " << n + 1 << ": ";
                for(int d = 0; d < nbDays; d++){
                    char shiftChar = 'O'; // Off = 0
                    for(int s = 0; s < 3; s++){
                        if(cp.getValue(schedule[idx(n,d,s)]) == 1){
                            if(s == 0) shiftChar = 'D'; // Day
                            else if(s == 1) shiftChar = 'E'; // Evening
                            else if(s == 2) shiftChar = 'N'; // Night
                        }
                    }
                    std::cout << shiftChar << " ";
                }
                std::cout << std::endl;
            }
        } else {
            std::cout << "No solution found." << std::endl;
        }
    } catch (IloException &ex) {
        std::cerr << "Error: " << ex << std::endl;
    }
    env.end();
    return 0;
}