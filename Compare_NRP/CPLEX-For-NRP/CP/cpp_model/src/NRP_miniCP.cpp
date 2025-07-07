#include "miniCPP.h"            // header gộp của MiniCPP
using namespace minicpp;

int main(int argc, char** argv)
{
    const int N = 4;                       // kích thước bàn cờ

    auto cp  = makeSolver();               // 1) tạo solver
    auto Col = intVarArray(cp, N, 0, N-1); // 2) N biến cột (hàng = chỉ số)

    // 3) Ràng buộc khác hàng chéo
    alldiff(cp, Col);                      // cột không trùng
    for (int i = 0; i < N; ++i)
        for (int j = i+1; j < N; ++j) {
            cp->post(abs(Col[i] - Col[j]) != j - i);   // chéo chính
        }

    // 4) Tìm kiếm DFS (first-fail)
    DFS<> dfs(cp, firstFail(Col));
    if (dfs.next()) {                      // lấy nghiệm đầu
        auto sol = dfs.solution();
        std::cout << "4-Queens solution:\n";
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c)
                std::cout << (sol[Col[r]] == c ? "Q " : ". ");
            std::cout << '\n';
        }
    }
    std::cout << "#DFS nodes = " << dfs.nodeCount() << '\n';
}
