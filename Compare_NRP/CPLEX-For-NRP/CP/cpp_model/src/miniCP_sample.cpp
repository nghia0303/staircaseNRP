#include <iostream>
#include "solver.hpp"
#include "intvar.hpp"
#include "constraint.hpp"
#include "search.hpp"

int main() {
    using namespace std;
    using namespace Factory;

    CPSolver::Ptr cp = Factory::makeSolver();

    // 10 biến nhị phân
    auto vars = Factory::intVarArray(cp, 10, 0, 1);

    // Ràng buộc tổng số biến đúng trong [2, 5]
    cp->post(sum(vars) >= 2);
    cp->post(sum(vars) <= 5);

    // Sử dụng DFSearch để liệt kê nghiệm
    DFSearch search(cp, [&]() {
        auto x = selectMin(vars,
            [](const auto& v) { return v->size() > 1; },
            [](const auto& v) { return v->size(); });
        if (x) {
            int c = x->min();
            return  [=] { cp->post(x == c); }
                  | [=] { cp->post(x != c); };
        } else return Branches({});
    });

    int count = 0;
    search.onSolution([&]() {
        cout << "Solution " << ++count << ": ";
        for (auto v : vars) cout << v->min() << " ";
        cout << endl;
    });

    search.solve();
    // cp->dealloc();
    return 0;
}