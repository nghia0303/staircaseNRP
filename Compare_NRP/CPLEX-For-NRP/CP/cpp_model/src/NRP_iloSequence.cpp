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
        
        // Tạo mảng 2 chiều schedule[n][d] với domain 0..3 (0: Day, 1: Evening, 2: Night, 3: Off)
        IloArray<IloIntVarArray> schedule(env, nurse);   // hàng
        for (int i = 0; i < nurse; ++i) {
            schedule[i] = IloIntVarArray(env, nbDays, 0, 3);  // cột
        }

        // Ràng buộc: Mỗi ca làm việc có thể là 0 (Off), 1 (Day), 2 (Evening), hoặc 3 (Night)
        // for (int n = 0; n < nurse; ++n) {
        //     for (int d = 0; d < nbDays; ++d) {
        //         for (int s = 0; s < 4; ++s) {
        //             model.add(schedule[n][d] >= 0); // ràng buộc "giữ chỗ" để solver biết đến schedule[n][d]
        //         }
        //     }
        // }

        // At most 1 shift per day
        // Ràng buộc: Mỗi ngày, mỗi y tá chỉ có thể làm một ca
        for (int n = 0; n < nurse; ++n) {
            for (int d = 0; d < nbDays; ++d) {
                IloExpr sum(env);
                for (int s = 0; s < 4; ++s) {
                    sum += schedule[n][d] == s; // Tính tổng số ca làm việc
                }
                model.add(sum == 1); // Ràng buộc tổng số ca làm việc trong
                // mỗi ngày phải bằng 1 (chỉ có một ca làm việc)
            }
        }

        // At most 6 shifts per 7 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                0,          // nbMin = 0
                6,          // nbMax = 6
                7,          // seqWidth = 7
                schedule[n], // tập hợp các biến
                IloIntArray(env, 3, 0, 1, 2), // giá trị của các ca làm việc
                IloIntVarArray(env, 3, 0, nbDays)  // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // At least 4 dayoffs per 14 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                4,          // nbMin = 4
                14, // nbMax = không giới hạn
                14,         // seqWidth = 14
                schedule[n], // tập hợp các biến
                IloIntArray(env, 1, 3), // giá trị của ca làm việc Off
                IloIntVarArray(env, 1, 0, nbDays)    // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // At least 4 and at most 8 evening shifts per 14 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                4,          // nbMin = 4
                8,          // nbMax = 8
                14,         // seqWidth = 14
                schedule[n], // tập hợp các biến
                IloIntArray(env, 1, 1), // giá trị của ca làm việc Evening
                IloIntVarArray(env, 1, 0, nbDays)    // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // At least msPer28 shifts per 28 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                msPer28,    // nbMin = msPer28
                28,  // nbMax = không giới hạn
                28,         // seqWidth = 28
                schedule[n], // tập hợp các biến
                IloIntArray(env, 3, 0, 1, 2), // giá trị của các ca làm việc
                IloIntVarArray(env, 3, 0, nbDays)  // không cần ràng buộc số lượng ca làm việc
            ));
        }
        
        // At most 2 night shifts per 7 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                0,          // nbMin = 0
                2,          // nbMax = 2
                7,          // seqWidth = 7
                schedule[n], // tập hợp các biến
                IloIntArray(env, 1, 2), // giá trị của ca làm việc Night
                IloIntVarArray(env, 1, 0, nbDays)    // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // At least 1 night shift per 14 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                1,          // nbMin = 1
                14, // nbMax = không giới hạn
                14,         // seqWidth = 14
                schedule[n], // tập hợp các biến
                IloIntArray(env, 1, 2), // giá trị của ca làm việc Night
                IloIntVarArray(env, 1, 0, nbDays)    // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // At least 2 and at most 4 evening or night shifts per 7 consecutive days
        for (int n = 0; n < nurse; n++){
            model.add(IloSequence(
                env,
                2,          // nbMin = 2
                4,          // nbMax = 4
                7,          // seqWidth = 7
                schedule[n], // tập hợp các biến
                IloIntArray(env, 2, 1, 2), // giá trị của ca làm việc Evening và Night
                IloIntVarArray(env, 2, 0, nbDays)    // không cần ràng buộc số lượng ca làm việc
            ));
        }

        // Two night shifts cannot occur in two consecutive days
        for (int n = 0; n < nurse; ++n) {
            for (int d = 0; d < nbDays - 1; ++d) {
                model.add(schedule[n][d] != 2 || schedule[n][d + 1] != 2);
            }
        }


        // ---------------------- Giải bài toán ----------------------
        IloCP cp(model);
        cp.setParameter(IloCP::LogVerbosity, IloCP::Terse);
        if (cp.solve()) {
            std::cout << "Nurse scheduling:" << std::endl;
            for (int n = 0; n < nurse; ++n) {
                std::cout << "Nurse " << n + 1 << ": ";
                for (int d = 0; d < nbDays; ++d) {
                    int shift = cp.getValue(schedule[n][d]);
                    // std::cout << shift << " "; // In ra ca làm việc của từng ngày
                    if (shift == 0) {
                        std::cout << "D ";
                    } else if (shift == 1) {
                        std::cout << "E ";
                    } else if (shift == 2) {
                        std::cout << "N ";
                    } else {
                        std::cout << "O ";
                    }
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