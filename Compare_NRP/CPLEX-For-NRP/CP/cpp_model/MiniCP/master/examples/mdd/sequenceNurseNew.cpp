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

#include <string>
#include <sstream>
#include <algorithm>
#include <iterator>
#include <regex>
#include <fstream> // std::ifstream
#include <iomanip>
#include <iostream>
#include <set>
#include <tuple>
#include <limits>
#include <iterator>
#include <climits>

#include "solver.hpp"
#include "trailable.hpp"
#include "intvar.hpp"
#include "constraint.hpp"
#include "search.hpp"
#include "mdd.hpp"
#include "RuntimeMonitor.hpp"
#include "mddrelax.hpp"
#include "mddConstraints.hpp"

#include "matrix.hpp"

using namespace Factory;
using namespace std;

template <class Vec>
Vec all(CPSolver::Ptr cp,const set<int>& over,const Vec& t)
{
   Vec res(over.size(),t.get_allocator()); //= Factory::intVarArray(cp, (int) over.size());
   int i = 0;
   for(auto e : over)
      res[i++] = t[e];
   return res;
}

std::string tab(int d)
{
  std::string s = "";
  while (d-- != 0)
    s = s + "  ";
  return s;
}

void addCumulSeq(CPSolver::Ptr cp, const Veci &vars, int N, int L, int U, const std::set<int> S)
{

  int H = vars.size();

  auto cumul = Factory::intVarArray(cp, H + 1, 0, H);
  cp->post(cumul[0] == 0);

  auto boolVar = Factory::boolVarArray(cp, H);
  for (int i = 0; i < H; i++)
  {
    cp->post(isMember(boolVar[i], vars[i], S));
  }

  for (int i = 0; i < H; i++)
  {
    cp->post(equal(cumul[i + 1], cumul[i], boolVar[i]));
  }

  for (int i = 0; i < H - N + 1; i++)
  {
    cp->post(cumul[i + N] <= cumul[i] + U);
    cp->post(cumul[i + N] >= cumul[i] + L);
  }
}

MDDRelax* newMDDRelax(CPSolver::Ptr cp, int relaxSize, int maxRebootDistance, int maxSplitIter, int nodePriorityAggregateStrategy, int candidatePriorityAggregateStrategy, bool useApproxEquiv, bool approxThenExact, int maxPriority) {
   auto mdd = new MDDRelax(cp,relaxSize,maxRebootDistance, relaxSize * maxSplitIter, approxThenExact, maxPriority);
   if (useApproxEquiv) {
      mdd->getSpec().useApproximateEquivalence();
   }
   mdd->getSpec().setNodePriorityAggregateStrategy(nodePriorityAggregateStrategy);
   mdd->getSpec().setCandidatePriorityAggregateStrategy(candidatePriorityAggregateStrategy);
   return mdd;
}


template <typename F>
void addMDDConstraint(CPSolver::Ptr cp, MDDRelax* mdd, int relaxSize, int maxRebootDistance, int maxSplitIter, int nodePriorityAggregateStrategy, int candidatePriorityAggregateStrategy, bool useApproxEquiv, bool approxThenExact, int maxConstraintPriority, bool sameMDD, F&& constraint) {
   if (!sameMDD) {
      mdd = newMDDRelax(cp, relaxSize, maxRebootDistance, maxSplitIter, nodePriorityAggregateStrategy, candidatePriorityAggregateStrategy, useApproxEquiv, approxThenExact, maxConstraintPriority);
   }
   constraint(mdd);
   if (!sameMDD) {
      cp->post(mdd);
   }
}

void addMDDAmongSequence(CPSolver::Ptr cp, MDDRelax* mdd, const Veci& vars, int H, int Q, int L, int U, const std::set<int>& S, const MDDOpts& opts){
  for (int i = 0; i <= H - Q; ++i)
  {
    // Tạo tập chỉ số các biến trong đoạn [i, i+Q1-1]
    set<int> amongVars;
    for (int j = i; j < i + Q; ++j)
    {
      amongVars.insert(j);
    }
    auto adv = all(cp, amongVars, vars);
    mdd->post(amongMDD2(mdd, adv, L, U, S, opts));
  }
}

void buildModel(
  CPSolver::Ptr cp, 
  int relaxSize, 
  int mode, 
  int nurse, 
  int day, 
  int maxRebootDistance, 
  int maxSplitIter, 
  int nodePriority, 
  int nodePriorityAggregateStrategy, 
  int candidatePriority, 
  int candidatePriorityAggregateStrategy, 
  bool useApproxEquiv, 
  bool approxThenExact, 
  int approxEquivMode, 
  int equivalenceThreshold, 
  bool sameMDD
)
{

  /***
   * Nurse scheduling problem from [Bergman, Cire, van Hoeve, JAIR 2014].
   * Determine the work schedule for a single nurse over time horizon {1..H}.
   *
   * Variable x[i] represents the assignment for day i, with domain {D, E, N, O}
   * (Day, Evening, Night, Off).
   *
   * Constraints:
   *  - at least 4 off-days every 14 days:                 Sequence(X, 14, 4, 14, {O})
   *  - at least 20 work shifts every 28 days:             Sequence(X, 28, 20, 28, {D, E, N})
   *  - between 1 and 4 night shifts every 14 days:        Sequence(X, 14, 1, 4, {N})
   *  - between 4 and 8 evening shifts every 14 days:      Sequence(X, 14, 4, 8, {E})
   *  - night shifts cannot appear on consecutive days:    Sequence(X, 2, 0, 1, {N})
   *  - between 2 and 4 evening/night shifts every 7 days: Sequence(X, 7, 2, 4, {E, N})
   *  - at most 6 work shifts every 7 days:                Sequence(X, 7, 0, 6, {D, E, N})
   *
   * The planning horizon H ranges from 40 to 100 days.
   ***/

  int H = day; // time horizon (number of days)

  int N = nurse; // number of nurses

  // vars[i] is shift on day i
  // mapping: 0 = Off, 1 = Day, 2 = Evening, 3 = Night
  // auto vars = Factory::intVarArray(cp, H, 0, 3);

  std::vector<Veci> schedule;
  for (int n = 0; n < N; ++n)
    schedule.push_back(Factory::intVarArray(cp, H, 0, 3));

  auto mdd = new MDDRelax(cp, relaxSize);

  int Q1 = 14, L1 = 4, U1 = 14;
  std::set<int> S1 = {0};
  int Q2 = 28, L2 = 20, U2 = 28;
  std::set<int> S2 = {1, 2, 3};
  int Q3 = 14, L3 = 1, U3 = 4;
  std::set<int> S3 = {3};
  int Q4 = 14, L4 = 4, U4 = 8;
  std::set<int> S4 = {2};
  int Q5 = 2, L5 = 0, U5 = 1;
  std::set<int> S5 = {3};
  int Q6 = 7, L6 = 2, U6 = 4;
  std::set<int> S6 = {2, 3};
  int Q7 = 7, L7 = 0, U7 = 6;
  std::set<int> S7 = {1, 2, 3};

  for (int n = 0; n < N; ++n)
  {
    auto &vars = schedule[n];
    // auto mdd = new MDDRelax(cp, relaxSize);
    if (mode == 0)
    {
      std::cout << "Cumulative Sums encoding" << endl;
      addCumulSeq(cp, vars, Q1, L1, U1, S1);
      addCumulSeq(cp, vars, Q2, L2, U2, S2);
      addCumulSeq(cp, vars, Q3, L3, U3, S3);
      addCumulSeq(cp, vars, Q4, L4, U4, S4);
      addCumulSeq(cp, vars, Q5, L5, U5, S5);
      addCumulSeq(cp, vars, Q6, L6, U6, S6);
      addCumulSeq(cp, vars, Q7, L7, U7, S7);
    }
    else if (mode == 1)
    {
      std::cout << "seqMDD encoding" << endl;
      mdd->post(seqMDD(mdd, vars, Q1, L1, U1, S1));
      mdd->post(seqMDD(mdd, vars, Q2, L2, U2, S2));
      mdd->post(seqMDD(mdd, vars, Q3, L3, U3, S3));
      mdd->post(seqMDD(mdd, vars, Q4, L4, U4, S4));
      mdd->post(seqMDD(mdd, vars, Q5, L5, U5, S5));
      mdd->post(seqMDD(mdd, vars, Q6, L6, U6, S6));
      mdd->post(seqMDD(mdd, vars, Q7, L7, U7, S7));
      cp->post(mdd);
    }
    else if (mode == 2)
    {
      std::cout << "seqMDD2 encoding" << endl;
      mdd->post(seqMDD2(mdd, vars, Q1, L1, U1, S1));
      mdd->post(seqMDD2(mdd, vars, Q2, L2, U2, S2));
      mdd->post(seqMDD2(mdd, vars, Q3, L3, U3, S3));
      mdd->post(seqMDD2(mdd, vars, Q4, L4, U4, S4));
      mdd->post(seqMDD2(mdd, vars, Q5, L5, U5, S5));
      mdd->post(seqMDD2(mdd, vars, Q6, L6, U6, S6));
      mdd->post(seqMDD2(mdd, vars, Q7, L7, U7, S7));
      cp->post(mdd);
    }
    else if (mode == 3)
    {
      std::cout << "seqMDD3 encoding" << endl;
      std::cout << "seqMDD3 encoding" << endl;
      mdd->post(seqMDD3(mdd, vars, Q1, L1, U1, S1));
      mdd->post(seqMDD3(mdd, vars, Q2, L2, U2, S2));
      mdd->post(seqMDD3(mdd, vars, Q3, L3, U3, S3));
      mdd->post(seqMDD3(mdd, vars, Q4, L4, U4, S4));
      mdd->post(seqMDD3(mdd, vars, Q5, L5, U5, S5));
      mdd->post(seqMDD3(mdd, vars, Q6, L6, U6, S6));
      mdd->post(seqMDD3(mdd, vars, Q7, L7, U7, S7));
      cp->post(mdd);
    }
    else if (mode == 4)
    {
      std::cout << "amongMDD2 encoding" << endl;
      
      MDDOpts opts = {
            .nodeP = nodePriority,
            .candP = candidatePriority,
            .appxEQMode = approxEquivMode,
            .eqThreshold = equivalenceThreshold
         };


      for (int n = 0; n < N; ++n)
      {
        std::cout << "Nurse " << n << ": ";
        auto &vars = schedule[n];
        // auto mdd = new MDDRelax(cp, relaxSize);
        if (!sameMDD) {
          MDDRelax* mdd = nullptr;

          mdd = newMDDRelax(
            cp, 
            relaxSize, 
            maxRebootDistance, 
            maxSplitIter, 
            nodePriorityAggregateStrategy, 
            candidatePriorityAggregateStrategy, 
            useApproxEquiv, 
            approxThenExact, 
            0
          );

          addMDDAmongSequence(cp, mdd, vars, H, Q1, L1, U1, S1, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q2, L2, U2, S2, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q3, L3, U3, S3, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q4, L4, U4, S4, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q5, L5, U5, S5, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q6, L6, U6, S6, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q7, L7, U7, S7, opts);
          cp->post(mdd);

        } else {
          addMDDAmongSequence(cp, mdd, vars, H, Q1, L1, U1, S1, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q2, L2, U2, S2, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q3, L3, U3, S3, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q4, L4, U4, S4, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q5, L5, U5, S5, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q6, L6, U6, S6, opts);
          addMDDAmongSequence(cp, mdd, vars, H, Q7, L7, U7, S7, opts);

          cp->post(mdd);
        }
        

        
      }



    }
  }

  // if (mode != 0)
  //   cp->post(mdd);

  Veci allVars = Factory::intVarArray(cp, N * H);
  int idx = 0;
  for (auto &row : schedule)
    for (auto &v : row)
      allVars[idx++] = v;

  DFSearch search(cp, [=]()
                  {                        
      unsigned i;
      // This is a lexicographic ordering search (skup bound variables)
      // ======================================================================
      for (i = 0u; i < allVars.size(); ++i)
            if (allVars[i]->size() > 1) break;
      auto x = (i < allVars.size()) ? allVars[i] : nullptr;
      if (x) {
            int c = x->min();
            return  [=] { cp->post(x == c); }
                 |  [=] { cp->post(x != c); };
        }
      return Branches({});


      // This block below computes the "depth" based on the number of bound variables.
      // ======================================================================
      // int depth = 0;
      // for(auto i=0u;i < vars.size();i++) 
      // 	depth += vars[i]->size() == 1;
      
      // This is a first fail search
      // ======================================================================
      // auto x = selectMin(vars,
      // 			 [](const auto& x) { return x->size() > 1;},
      // 			 [](const auto& x) { return x->size();});
     
      if (x) {
        int c = x->min();	
        return  [=] {
                        //cout << tab(depth) << "?x(" << i << ") == " << c << " " <<  x << endl;
            cp->post(x == c);
            //cout << tab(depth) << "!x(" << i << ") == " << c << " " <<  x << endl;
          }
          | [=] {
                    //cout << tab(depth) << "?x(" << i << ") != " << c << " " <<  x << endl;
              cp->post(x != c);
              //cout << tab(depth) << "!x(" << i << ") != " << c << " " <<  x << endl;
            };
      } else return Branches({}); });

  search.onSolution([&schedule, N, H]()
                    {
    for (int n = 0; n < N; ++n) {
      std::cout << "Nurse " << n << " : " << schedule[n] << '\n';
    }
    std::cout << "-----------------------------\n"; });

  auto start = RuntimeMonitor::cputime();

  auto stat = search.solve([](const SearchStatistics &stats)
                           {
      //      return stats.numberOfSolutions() > INT_MAX;
      return stats.numberOfSolutions() > 0; });
  std::cout << stat << endl;

  auto end = RuntimeMonitor::cputime();
  extern int iterMDD;
  // extern int nbCS;
  std::cout << "solns: " << stat.numberOfSolutions() << '\n';
  std::cout << "Time : " << RuntimeMonitor::milli(start, end) << '\n';
  std::cout << "I/C  : " << (double)iterMDD / stat.numberOfNodes() << '\n';
  // std::cout << "#CS  : " << nbCS << '\n';
  // std::cout << "#L   : " << mdd->nbLayers() << '\n';
}

int main(int argc, char *argv[])
{
  int width = (argc >= 2 && strncmp(argv[1], "-w", 2) == 0) ? atoi(argv[1] + 2) : 1;
  int mode = (argc >= 3 && strncmp(argv[2], "-m", 2) == 0) ? atoi(argv[2] + 2) : 1;
  // int nurse = (argc >= 4 && strncmp(argv[3], "-nurse", 6) == 0) ? atoi(argv[3] + 6) : 1;
  // int day = (argc >= 5 && strncmp(argv[4], "-day", 4) == 0) ? atoi(argv[4] + 4) : 40;

  int maxRebootDistance = (argc >= 4 && strncmp(argv[3],"-r",2)==0) ? atoi(argv[3]+2) : INT_MAX;
   int maxSplitIter = (argc >= 5 && strncmp(argv[4],"-i",2)==0) ? atoi(argv[4]+2) : INT_MAX;
  //  int constraintSet = (argc >= 6 && strncmp(argv[5],"-c",2)==0) ? atoi(argv[5]+2) : 1;
   int nurse = (argc >= 6 && strncmp(argv[5], "-nurse", 6) == 0) ? atoi(argv[5] + 6) : 1;
  //  int horizonSize = (argc >= 7 && strncmp(argv[6],"-h",2)==0) ? atoi(argv[6]+2) : 40;
   int day = (argc >= 7 && strncmp(argv[6], "-day", 4) == 0) ? atoi(argv[6] + 4) : 40;
   int nodePriority = (argc >= 8 && strncmp(argv[7],"-n",2)==0) ? atoi(argv[7]+2) : 0;
   int nodePriorityAggregateStrategy = (argc >= 9 && strncmp(argv[8],"-na",3)==0) ? atoi(argv[8]+3) : 1;
   int candidatePriority = (argc >= 10 && strncmp(argv[9],"-d",2)==0) ? atoi(argv[9]+2) : 0;
   int candidatePriorityAggregateStrategy = (argc >= 11 && strncmp(argv[10],"-ca",3)==0) ? atoi(argv[10]+3) : 1;
   bool useApproxEquiv = (argc >= 12 && strncmp(argv[11],"-a",2)==0) ? atoi(argv[11]+2) : true;
   bool approxThenExact = (argc >= 13 && strncmp(argv[12],"-e",2)==0) ? atoi(argv[12]+2) : true;
   int approxEquivMode = (argc >= 14 && strncmp(argv[13],"-p",2)==0) ? atoi(argv[13]+2) : 0;
   int equivalenceThreshold = (argc >= 15 && strncmp(argv[14],"-t",2)==0) ? atoi(argv[14]+2) : 3;
   int maxWorkConstraintPriority = (argc >= 16 && strncmp(argv[15],"-maxP",5)==0) ? atoi(argv[15]+5) : 0;
   int minWorkConstraintPriority = (argc >= 17 && strncmp(argv[16],"-minP",5)==0) ? atoi(argv[16]+5) : 0;
   int weeklyWorkConstraintPriority = (argc >= 18 && strncmp(argv[17],"-wP",3)==0) ? atoi(argv[17]+3) : 0;
  bool sameMDD = (argc >= 19 && strncmp(argv[18],"-j",2)==0) ? atoi(argv[18]+2) : true;
  // mode: 0 (cumulative sums encoding), >=1 (MDD)

  std::cout << "width = " << width << std::endl;
  std::cout << "mode = " << mode << std::endl;
  std::cout << "nurse = " << nurse << std::endl;
  std::cout << "day = " << day << std::endl;

  try
  {
    CPSolver::Ptr cp = Factory::makeSolver();
    buildModel(cp, width, mode, nurse, day, maxRebootDistance, maxSplitIter, nodePriority, nodePriorityAggregateStrategy, candidatePriority, candidatePriorityAggregateStrategy, useApproxEquiv, approxThenExact, approxEquivMode, equivalenceThreshold, sameMDD);
  }
  catch (Status s)
  {
    std::cout << "model infeasible during post" << std::endl;
  }
  catch (std::exception &e)
  {
    std::cerr << "Unable to find the file" << std::endl;
  }

  return 0;
}
