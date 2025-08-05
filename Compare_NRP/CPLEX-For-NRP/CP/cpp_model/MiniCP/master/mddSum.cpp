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

#include "mddConstraints.hpp"
#include "mddnode.hpp"
#include <limits.h>
#include <algorithm>
#include <numeric>

namespace Factory {

   MDDCstrDesc::Ptr sum(MDD::Ptr m,std::initializer_list<var<int>::Ptr> vars,int lb, int ub) {
      CPSolver::Ptr cp = (*vars.begin())->getSolver();
      auto theVars = Factory::intVarArray(cp,vars.size(),[&vars](int i) {
         return std::data(vars)[i];
      });      
      const std::vector<int> theCoefs(vars.size(),1);
      return sum(m,theVars,theCoefs,lb,ub);
   }
   MDDCstrDesc::Ptr sum(MDD::Ptr m,std::initializer_list<var<int>::Ptr> vars,var<int>::Ptr z)
   {
      CPSolver::Ptr cp = (*vars.begin())->getSolver();
      auto theVars = Factory::intVarArray(cp,vars.size(),[&vars](int i) {
         return std::data(vars)[i];
      });
      return sum(m,theVars,z);
   }
   MDDCstrDesc::Ptr sum(MDD::Ptr m,std::initializer_list<var<int>::Ptr> vars,std::initializer_list<int> array, int lb, int ub) {
      CPSolver::Ptr cp = (*vars.begin())->getSolver();
      auto theVars = Factory::intVarArray(cp,vars.size(),[&vars](int i) {
         return std::data(vars)[i];
      });
      const std::vector<int> theCoefs = array;
      return sum(m,theVars,theCoefs,lb,ub);
   }
   MDDCstrDesc::Ptr sum(MDD::Ptr m,std::vector<var<int>::Ptr> vars,int lb, int ub) {
     CPSolver::Ptr cp = vars[0]->getSolver();
     auto theVars = Factory::intVarArray(cp,vars.size(),[&vars](int i) {
       return vars[i];
     });
     const std::vector<int> theCoefs(vars.size(),1);
     return sum(m,theVars,theCoefs,lb,ub);
   }

   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Veci& vars, const std::vector<int>& array, int lb, int ub) {
      // Enforce
      //   sum(i, array[i]*vars[i]) >= lb and
      //   sum(i, array[i]*vars[i]) <= ub
      MDDSpec& mdd = m->getSpec();
      const int nbVars = (int)vars.size();      
      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states: min and max weighted value (initialize at 0, maximum is INT_MAX (when negative values are allowed).
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len    = mdd.downIntState(d, 0, vars.size(),MinFun); // captures the index i, to express array[i]*val when vars[i]=val.
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MinFun);

      // The lower bound needs the bottom-up state information to be effective.
      mdd.arcExist(d,[=] (const auto& parent,const auto& child, var<int>::Ptr var, const auto& val) -> bool {
         return (parent.down[minW] + val*array[parent.down[len]] + child.up[minWup] <= ub) &&
            (parent.down[maxW] + val*array[parent.down[len]] + child.up[maxWup] >= lb);
      });
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= ub) && (n.down[maxW] + n.up[maxWup] >= lb);
      });

      mdd.transitionDown(d,minW,{len,minW},{},[minW,array,len](auto& out,const auto& parent,const auto&,const auto& val) {
         out[minW] = parent.down[minW] + array[parent.down[len]] * val.min();
      });
      mdd.transitionDown(d,maxW,{len,maxW},{},[maxW,array,len] (auto& out,const auto& parent,const auto&,const auto& val) {
         out[maxW] = parent.down[maxW] + array[parent.down[len]] * val.max();
      });
      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto&, const auto&) {
         out[len]  = parent.down[len] + 1;
      });

      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[nbVars,minWup,array,lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            const auto coef = array[nbVars - child.up[lenUp]-1];
            out[minWup] = child.up[minWup] + coef * val.min();
         }
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[nbVars,maxWup,array,lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            const auto coef = array[nbVars - child.up[lenUp]-1];
            out[maxWup] = child.up[maxWup] + coef * val.max();
         }
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto&, const auto&) {
         out[lenUp] = child.up[lenUp] + 1;
      });
      return d;
   }

   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Vecb& vars, var<int>::Ptr z, Objective::Ptr objective) {
      // Enforce MDD bounds consistency on
      //   sum(i, vars[i]) == z
      MDDSpec& mdd = m->getSpec();
      const int nbVars = (int)vars.size();
      mdd.addGlobal({z});
      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len  = mdd.downIntState(d, 0, vars.size(),MaxFun); // 'len' captures the index i, to express val when vars[i]=val.
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MaxFun);

      mdd.arcExist(d,[=] (const auto& parent,const auto& child, var<int>::Ptr var, const auto& val) -> bool {
         if (child.up.unused()) return parent.down[maxW] + val + (nbVars - parent.down[len] - 1) >= z->min();
         return ((parent.down[minW] + val + child.up[minWup] <= z->max()) &&
                 (parent.down[maxW] + val + child.up[maxWup] >= z->min()));
      });
 
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= z->max()) && (n.down[maxW] + n.up[maxWup] >= z->min());
      });

      mdd.transitionDown(d,minW,{minW},{},[minW] (auto& out,const auto& parent,const auto&, const auto& val) {
         out[minW] = parent.down[minW] + val.min();
      });
      mdd.transitionDown(d,maxW,{maxW},{},[maxW] (auto& out,const auto& parent,const auto&, const auto& val) {
         out[maxW] =  parent.down[maxW] + val.max();
      });

      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[nbVars,minWup,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) 
            out[minWup] = child.up[minWup] + val.min();         
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[nbVars,maxWup,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) 
            out[maxWup] = child.up[maxWup] + val.max();
      });

      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto& var, const auto& val) {
         out[len] = parent.down[len] + 1;
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto& var, const auto& val) {
         out[lenUp] = child.up[lenUp] + 1;
      });
      mdd.onFixpoint([z,minW,maxW](const auto& sink) {
         z->updateBounds(sink.down[minW],sink.down[maxW]);
      });
      if (objective) {
         if (objective->isMin()) {
            mdd.onRestrictedFixpoint([objective,minW,maxW](const auto& sink) {
               objective->foundPrimal(sink.down[minW]);
            });
         } else {
            mdd.onRestrictedFixpoint([objective,maxW](const auto& sink) {
               objective->foundPrimal(sink.down[maxW]);
            });
         }
      }
      return d;
   }
   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Veci& vars, var<int>::Ptr z) {
      // Enforce MDD bounds consistency on
      //   sum(i, vars[i]) == z
      MDDSpec& mdd = m->getSpec();
      mdd.addGlobal({z});
      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len  = mdd.downIntState(d, 0, vars.size(),MaxFun); // captures the index i, to express val when vars[i]=val.
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MaxFun);

      mdd.arcExist(d,[=] (const auto& parent,const auto& child, var<int>::Ptr var, const auto& val) {
         return ((parent.down[minW] + val + child.up[minWup] <= z->max()) &&
                 (parent.down[maxW] + val + child.up[maxWup] >= z->min()));
      });
 
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= z->max()) && (n.down[maxW] + n.up[maxWup] >= z->min());
      });

      mdd.transitionDown(d,minW,{minW},{},[minW] (auto& out,const auto& parent,const auto&, const auto& val) {
         out[minW] = parent.down[minW] + val.min();
      });
      mdd.transitionDown(d,maxW,{maxW},{},[maxW] (auto& out,const auto& parent,const auto&, const auto& val) {
         out[maxW] =  parent.down[maxW] + val.max();
      });

      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[minWup,lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[minWup] =  child.up[minWup] + val.min();
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[maxWup,lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[maxWup] =  child.up[maxWup] + val.max();
      });

      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto&, const auto& val) {
         out[len] = parent.down[len] + 1;
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[lenUp] = child.up[lenUp] + 1;
      });
      mdd.onFixpoint([z,minW,maxW](const auto& sink) {
         z->updateBounds(sink.down[minW],sink.down[maxW]);
      });
      return d;
   }


   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Veci& vars, const std::vector<int>& array, var<int>::Ptr z) {
      // Enforce MDD bounds consistency on
      //   sum(i, array[i]*vars[i]) == z
      MDDSpec& mdd = m->getSpec();
      mdd.addGlobal({z});
      const int nbVars = (int)vars.size();

      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len  = mdd.downIntState(d, 0, vars.size(),MaxFun); // captures the index i, to express array[i]*val when vars[i]=val.
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MaxFun);

      mdd.arcExist(d,[=] (const auto& parent,const auto& child,var<int>::Ptr var, const auto& val) {
         return ((parent.down[minW] + val*array[parent.down[len]] + child.up[minWup] <= z->max()) &&
                 (parent.down[maxW] + val*array[parent.down[len]] + child.up[maxWup] >= z->min()));
      });
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= z->max()) && (n.down[maxW] + n.up[maxWup] >= z->min());
      });

      mdd.transitionDown(d,minW,{len,minW},{},[minW,array,len] (auto& out,const auto& parent,const auto&, const auto& val) {
         auto coef = array[parent.down[len]];
         out[minW] = parent.down[minW] + coef * val.min();
      });
      mdd.transitionDown(d,maxW,{len,maxW},{},[maxW,array,len] (auto& out,const auto& parent,const auto&, const auto& val) {
         auto coef = array[parent.down[len]];
         out[maxW] =  parent.down[maxW] + coef * val.max();
      });

      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[nbVars,minWup,array,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            auto coef = array[nbVars - child.up[lenUp]-1];
            out[minWup] =  child.up[minWup] + coef * val.min();
         }
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[nbVars,maxWup,array,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            auto coef = array[nbVars - child.up[lenUp]-1];
            out[maxWup] =  child.up[maxWup] + coef * val.max();
         }
      });

      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto&, const auto& val) {
         out[len] = parent.down[len] + 1;
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[lenUp] = child.up[lenUp] + 1;
      });

      mdd.onFixpoint([z,minW,maxW](const auto& sink) {
         z->updateBounds(sink.down[minW],sink.down[maxW]);
      });
      return d;
   }

   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Vecb& vars, const std::vector<int>& array, var<int>::Ptr z, Objective::Ptr objective) {
      // Enforce MDD bounds consistency on
      //   sum(i, array[i]*vars[i]) == z
      MDDSpec& mdd = m->getSpec();
      mdd.addGlobal({z});
      const int nbVars = (int)vars.size();

      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len  = mdd.downIntState(d, 0, vars.size(),MaxFun); // captures the index i, to express array[i]*val when vars[i]=val.
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MaxFun);

      std::vector<int> RUB(nbVars);
      int sumUp = 0;
      for (int i = nbVars - 1; i >= 0; i--) {
         RUB[i] = sumUp;
         sumUp += std::max(0, array[i]);
      }

      mdd.arcExist(d,[=] (const auto& parent,const auto& child,var<int>::Ptr var, const auto& val) {
         if (child.up.unused()) {
            return parent.down[maxW] + val*array[parent.down[len]] + RUB[parent.down[len]] >= z->min();
         }
         int upperBoundBelow = std::max((int)child.up[maxWup], RUB[parent.down[len]]);
         return ((parent.down[minW] + val*array[parent.down[len]] + child.up[minWup] <= z->max()) &&
                 (parent.down[maxW] + val*array[parent.down[len]] + upperBoundBelow >= z->min()));
      });
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= z->max()) && (n.down[maxW] + n.up[maxWup] >= z->min());
      });

      mdd.transitionDown(d,minW,{len,minW},{},[minW,array,len] (auto& out,const auto& parent,const auto&, const auto& val) {
         auto coef = array[parent.down[len]];
         if (coef > 0) {
            out[minW] = parent.down[minW] + coef * val.min();
         } else if (coef < 0) {
            out[minW] = parent.down[minW] + coef * val.max();
         } else {
            out[minW] = parent.down[minW];
         }
      });
      mdd.transitionDown(d,maxW,{len,maxW},{},[maxW,array,len] (auto& out,const auto& parent,const auto&, const auto& val) {
         auto coef = array[parent.down[len]];
         if (coef > 0) {
            out[maxW] = parent.down[maxW] + coef * val.max();
         } else if (coef < 0) {
            out[maxW] = parent.down[maxW] + coef * val.min();
         } else {
            out[maxW] = parent.down[maxW];
         }
      });

      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[nbVars,minWup,array,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            auto coef = array[nbVars - child.up[lenUp]-1];
            if (coef > 0) {
               out[minWup] = child.up[minWup] + coef * val.min();
            } else if (coef < 0) {
               out[minWup] = child.up[minWup] + coef * val.max();
            } else {
               out[minWup] = child.up[minWup];
            }
         }
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[nbVars,maxWup,array,lenUp] (auto& out,const auto& child,const auto&, const auto& val) {
         if (child.up[lenUp] < nbVars) {
            auto coef = array[nbVars - child.up[lenUp]-1];
            if (coef > 0) {
               out[maxWup] = child.up[maxWup] + coef * val.max();
            } else if (coef < 0) {
               out[maxWup] = child.up[maxWup] + coef * val.min();
            } else {
               out[maxWup] = child.up[maxWup];
            }
         }
      });

      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto&, const auto& val) {
         out[len] = parent.down[len] + 1;
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[lenUp] = child.up[lenUp] + 1;
      });

      mdd.onFixpoint([z,minW,maxW](const auto& sink) {
         z->updateBounds(sink.down[minW],sink.down[maxW]);
      });

      if (objective) {
         if (objective->isMin()) {
            mdd.onRestrictedFixpoint([objective,minW,maxW](const auto& sink) {
               objective->foundPrimal(sink.down[minW]);
            });
         } else {
            mdd.onRestrictedFixpoint([objective,maxW](const auto& sink) {
               objective->foundPrimal(sink.down[maxW]);
            });
         }
      }

      mdd.splitOnLargest([maxW](const auto& in) { return in.getDownState()[maxW];});
      mdd.candidateByLargest([maxW](const auto& state, void* arcs, int numArcs) {
         return state[maxW];
      });
      return d;
   }

   MDDCstrDesc::Ptr sum(MDD::Ptr m, const Factory::Veci& vars, const std::vector<std::vector<int>>& matrix, var<int>::Ptr z) {
      // Enforce MDD bounds consistency on
      //   sum(i, matrix[i][vars[i]]) == z
      MDDSpec& mdd = m->getSpec();
      mdd.addGlobal({z});
      const int nbVars = (int)vars.size();
      auto d = mdd.makeConstraintDescriptor(vars,"sumMDD");

      // Define the states
      const auto minW = mdd.downIntState(d, 0, INT_MAX,MinFun);
      const auto maxW = mdd.downIntState(d, 0, INT_MAX,MaxFun);
      const auto minWup = mdd.upIntState(d, 0, INT_MAX,MinFun);
      const auto maxWup = mdd.upIntState(d, 0, INT_MAX,MaxFun);
      const auto len  = mdd.downIntState(d, 0, vars.size(),MaxFun); // captures the index i, to express matrix[i][vars[i]]
      const auto lenUp  = mdd.upIntState(d, 0, vars.size(),MaxFun);

      mdd.arcExist(d,[=] (const auto& parent,const auto& child,var<int>::Ptr var, const auto& val) {
         const int mlv = matrix[parent.down[len]][val];
         return ((parent.down[minW] + mlv + child.up[minWup] <= z->max()) &&
                 (parent.down[maxW] + mlv + child.up[maxWup] >= z->min()));
      });
      mdd.nodeExist([=](const auto& n) {
        return (n.down[minW] + n.up[minWup] <= z->max()) && (n.down[maxW] + n.up[maxWup] >= z->min());
      });


      mdd.transitionDown(d,minW,{len,minW},{},[minW,matrix,len] (auto& out,const auto& parent,const auto&, const auto& val) {
         int delta = std::numeric_limits<int>::max();
         const auto& row = matrix[parent.down[len]];
         for(int v : val)
            delta = std::min(delta,row[v]);
         out[minW] = parent.down[minW] + delta;
      });
      mdd.transitionDown(d,maxW,{len,maxW},{},[maxW,matrix,len] (auto& out,const auto& parent,const auto&,const auto& val) {
         int delta = std::numeric_limits<int>::min();
         const auto& row = matrix[parent.down[len]];
         for(int v : val)
            delta = std::max(delta,row[v]);
         out[maxW] = parent.down[maxW] + delta;
      });
      mdd.transitionUp(d,minWup,{lenUp,minWup},{},[nbVars,minWup,matrix,lenUp](auto& out,const auto& child,const auto&,const auto& val) {
         if (child.up[lenUp] < nbVars) {
            int delta = std::numeric_limits<int>::max();
            const auto& row = matrix[nbVars - child.up[lenUp]-1];
            for(int v : val)
               delta = std::min(delta,row[v]);
            out[minWup] = child.up[minWup] + delta;
         }
      });
      mdd.transitionUp(d,maxWup,{lenUp,maxWup},{},[nbVars,maxWup,matrix,lenUp](auto& out,const auto& child,const auto&,const auto& val) {
         if (child.up[lenUp] < nbVars) {
            int delta = std::numeric_limits<int>::min();
            const auto& row = matrix[nbVars - child.up[lenUp]-1];
            for(int v : val)
               delta = std::max(delta,row[v]);
            out[maxWup] = child.up[maxWup] + delta;
         }
      });

      mdd.transitionDown(d,len,{len},{},[len](auto& out,const auto& parent,const auto&, const auto& val) {
         out[len] =   parent.down[len] + 1;
      });
      mdd.transitionUp(d,lenUp,{lenUp},{},[lenUp](auto& out,const auto& child,const auto&, const auto& val) {
         out[lenUp] =   child.up[lenUp] + 1;
      });

      mdd.onFixpoint([z,minW,maxW](const auto& sink) {
         z->updateBounds(sink.down[minW],sink.down[maxW]);
      });

      mdd.splitOnLargest([maxW](const auto& in) { return in.getDownState()[maxW];});
      mdd.candidateByLargest([maxW](const auto& state, void* arcs, int numArcs) {
         return state[maxW];
      });

      mdd.bestValue([=](auto layer) {
         int bestValue = 0;
         int bestWeight = 0;
         int bestArcWeight = 0;
         for (auto& node : *layer) {
            for (auto& childArc : node->getChildren()) {
               auto child = childArc->getChild();
               //int childWeight = child->getDownState()[maxW];
               //int childWeight = child->getDownState()[minW];
               int childWeight = child->getDownState()[maxW] + child->getUpState()[maxWup];
               //int childWeight = child->getDownState()[minW] + child->getUpState()[minWup];
               int arcWeight = matrix[node->getDownState()[len]][childArc->getValue()];
               if (childWeight > bestWeight || (childWeight == bestWeight && arcWeight > bestArcWeight)) {
                  bestWeight = childWeight;
                  bestValue = childArc->getValue();
                  bestArcWeight = arcWeight;
               }
            }
         }
         return bestValue;
      });

      return d;
   }
}
