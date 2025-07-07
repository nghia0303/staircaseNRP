#include <ilcp/cp.h>

int main(){
    IloEnv env;
    IloModel model(env);


    const int DAYS = 30;

    IloIntVarArray shift(env, DAYS, 0, 1);  
    
    for (int i = 0; i < DAYS; i++) {
        model.add(shift[i] >= 0); // ràng buộc "giữ chỗ" để solver biết đến shift[i]
    }

    IloIntVarArray subset(env);
    for(int d=0; d<DAYS/2; ++d)
        subset.add(shift[d]);

    IloIntArray    nightVal(env, 1, 1);         
    IloIntVarArray card(env, 1, 0, DAYS);       

    
    model.add(IloSequence(env,
                          1,          // nbMin
                          3,          // nbMax
                          5,          // seqWidth = 5
                          subset,     // tập hợp các biến
                          nightVal,
                          card));     // nếu không cần, có thể dùng IloIntVarArray()

    // ví dụ: đúng 4 ca đêm / tuần
    // model.add(card[0] == 4);
    std::cout << card;

    IloCP cp(model);
    cp.setParameter(IloCP::LogVerbosity, IloCP::Quiet);
    if (cp.solve()){
        for(int d=0; d<DAYS; ++d)
            std::cout << cp.getValue(shift[d]) << ' ';
        std::cout << std::endl;
    }
    env.end();
}
