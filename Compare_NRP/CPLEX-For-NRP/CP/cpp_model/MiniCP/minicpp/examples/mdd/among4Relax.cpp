/*
 * mini-cp is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License  v3
 * as published by the Free Software Foundation.
 *
 * mini-cp is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY.
 * See the GNU Lesser General Public License  for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with mini-cp. If not, see http://www.gnu.org/licenses/lgpl-3.0.en.html
 *
 * Copyright (c)  2018. by Laurent Michel, Pierre Schaus, Pascal Van Hentenryck
 */

#include "solver.hpp"
#include "trailable.hpp"
#include "intvar.hpp"
#include "constraint.hpp"
#include "search.hpp"
#include "mdd.hpp"
#include "RuntimeMonitor.hpp"
#include "mddrelax.hpp"
#include "mddConstraints.hpp"

#include <iostream>
#include <iomanip>

int main(int argc,char* argv[])
{
   int useSearch = 1;
   using namespace Factory;
   int width = (argc >= 2 && strncmp(argv[1],"-w",2)==0) ? atoi(argv[1]+2) : 16;
      
   CPSolver::Ptr cp  = Factory::makeSolver();

   auto v = Factory::intVarArray(cp, 50, 1, 9);
   auto start = RuntimeMonitor::now();
   auto mdd = new MDDRelax(cp,width);
   //auto mdd = new MDD(cp);
   Factory::amongMDD(mdd->getSpec(),v, 2, 5, {2});
   Factory::amongMDD(mdd->getSpec(),v, 2, 5, {3});
   Factory::amongMDD(mdd->getSpec(),v, 3, 5, {4});
   Factory::amongMDD(mdd->getSpec(),v, 3, 5, {5});

   cp->post(mdd);

   std::cout << "MDD Usage: " << mdd->usage() << std::endl;
   auto dur = RuntimeMonitor::elapsedSince(start);
   //   mdd->saveGraph();
   std::cout << "Time : " << dur << std::endl;
  
   if(useSearch){
      DFSearch search(cp,[=]() {
         unsigned i;
         for(i=0u;i< v.size();i++)
            if (v[i]->size() > 1)
               break;
         auto x = v[i];
/*
                            auto x = selectMin(v,
                                               [](const auto& x) { return x->size() > 1;},
                                               [](const auto& x) { return x->size();});
          */
         if (x) {
            int c = x->min();
            return  [=] {
                       //std::cout << "branch(" << i << ") ==" << c << std::endl;
                       cp->post(x == c);
                       // mdd->debugGraph();
                    }
               | [=] {
                    cp->post(x != c);
                    // std::cout << "branch!=" << std::endl;
                    // mdd->debugGraph();
                 };
         } else return Branches({});
                         });
      
      search.onSolution([&v]() {
                           std::cout << "Assignment:" << v << '\n';
                           int count[10] = {};
                           for(int k=0;k < 50;k++) {
                              count[v[k]->min()]++;
                           }
                           bool c1 = (2 <= count[2] && count[2] <= 5);
                           bool c2 = (2 <= count[3] && count[3] <= 5);
                           bool c3 = (3 <= count[4] && count[4] <= 5);
                           bool c4 = (3 <= count[5] && count[5] <= 5);
                           if (c1 && c2 && c3 && c4)
                              std::cout << "All good!\n";
                           else std::cout << "Something wrong...\n";
                        });
      
      std::cout << "starting..." << std::endl;
      auto stat = search.solve([](const SearchStatistics& stats) {
                                  return stats.numberOfSolutions() > 0;
                               });
      std::cout << stat << std::endl;
      auto end = RuntimeMonitor::now();
      extern int iterMDD;
      extern int nbCS;
      std::cout << "{ \"JSON\" :\n {";
      std::cout << "\n\t\"among4Relax\" :" << "{\n";
      std::cout << "\t\t\"m\" : " << 1 << ",\n";
      std::cout << "\t\t\"w\" : " << width << ",\n";
      std::cout << "\t\t\"nodes\" : " << stat.numberOfNodes() << ",\n";
      std::cout << "\t\t\"fails\" : " << stat.numberOfFailures() << ",\n";
      std::cout << "\t\t\"iter\" : " << iterMDD << ",\n";
      std::cout << "\t\t\"nbCS\" : " << nbCS << ",\n";
      std::cout << "\t\t\"layers\" : " << mdd->nbLayers() << ",\n";
      std::cout << "\t\t\"time\" : " << RuntimeMonitor::milli(start,end) << "\n";
      std::cout << "\t}\n";  
      std::cout << "}\n}";

   }
   //cp.dealloc();
   return 0;
}

