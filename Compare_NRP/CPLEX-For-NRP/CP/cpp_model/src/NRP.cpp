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

        // At most 6 shifts per 7 consecutive daysint argc, char** argv
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 7; d++){
                IloExpr sum(env);
                for(int offset = 0; offset < 7; offset++){
                    for(int s = 0; s < 3; s++){
                        sum += schedule[idx(n, d + offset, s)];
                    }
                }
                model.add(sum <= 6);
                sum.end();
            }
        }

        // At least 4 dayoffs per 14 consecutive days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 14; d++){
                IloExpr dayOffCount(env);
                for(int offset = 0; offset < 14; offset++){
                    IloExpr assigned(env);
                    for(int s = 0; s < 3; s++){
                        assigned += schedule[idx(n, d + offset, s)];
                    }
                    // assigned == 0 => off => +1
                    // Cách dùng: dayOffCount += (assigned == 0)
                    // Không có so sánh trực tiếp, ta có thể dùng mánh: 
                    //     assigned <= 0 => assigned == 0 => dayOff = 1
                    // Hoặc IloIfThen, tùy biến.
                    // Đơn giản: dayOffCount += (1 - assigned) >= ...
                    // (Miễn là assigned <= 1)
                    dayOffCount += (1 - assigned);
                    assigned.end();
                }
                model.add(dayOffCount >= 4);
                dayOffCount.end();
            }
        }

        // At least 4 and at most 8 evening shifts (s=1) per 14 days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 14; d++){
                IloExpr eSum(env);
                for(int offset = 0; offset < 14; offset++){
                    eSum += schedule[idx(n, d + offset, 1)];
                }
                model.add(eSum >= 4);
                model.add(eSum <= 8);
                eSum.end();
            }
        }

        // At least msPer28 shifts per 28 consecutive days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 28; d++){
                IloExpr sum28(env);
                for(int offset = 0; offset < 28; offset++){
                    for(int s = 0; s < 3; s++){
                        sum28 += schedule[idx(n, d + offset, s)];
                    }
                }
                model.add(sum28 >= msPer28);
                sum28.end();
            }
        }

        // At most 2 night shifts (s=2) per 7 consecutive days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 7; d++){
                IloExpr nSum(env);
                for(int offset = 0; offset < 7; offset++){
                    nSum += schedule[idx(n, d + offset, 2)];
                }
                model.add(nSum <= 2);
                nSum.end();
            }
        }

        // At least 1 night shift (s=2) per 14 consecutive days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 14; d++){
                IloExpr nSum(env);
                for(int offset = 0; offset < 14; offset++){
                    nSum += schedule[idx(n, d + offset, 2)];
                }
                model.add(nSum >= 1);
                nSum.end();
            }
        }

        // 2-4 evening or night shifts (s=1 or s=2) per 7 days
        for(int n = 0; n < nurse; n++){
            for(int d = 0; d <= nbDays - 7; d++){
                IloExpr enSum(env);
                for(int offset = 0; offset < 7; offset++){
                    enSum += schedule[idx(n, d + offset, 1)];
                    enSum += schedule[idx(n, d + offset, 2)];
                }
                model.add(enSum >= 2);
                model.add(enSum <= 4);
                enSum.end();
            }
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