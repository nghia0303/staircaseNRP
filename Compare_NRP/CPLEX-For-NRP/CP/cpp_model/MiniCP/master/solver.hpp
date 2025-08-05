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

#ifndef __SOLVER_H
#define __SOLVER_H

#include <list>
#include <deque>
#include <functional>
#include <stdlib.h>
#include <setjmp.h>
#include "handle.hpp"
#include "fail.hpp"
#include "store.hpp"
#include "avar.hpp"
#include "acstr.hpp"
#include "trailable.hpp"

typedef std::reference_wrapper<std::function<void(void)>> Closure;
class Controller;
class Tracer;
class Checkpoint;

class DEPQueue {
   std::deque<Constraint::Ptr>  _q[2];
public:
   DEPQueue() {}
   void enQueue(Constraint::Ptr& c) {
      _q[c->getPriority()].emplace_back(c);
   }
   bool empty() const { return _q[0].empty() && _q[1].empty();}
   auto size() const  { return _q[0].size() + _q[1].size();}
   Constraint::Ptr deQueue() {
      if (!_q[Constraint::CHIGH].empty()) {
         auto c = _q[Constraint::CHIGH].front();
         _q[Constraint::CHIGH].pop_front();
         return c;
      } else {
         auto c = _q[Constraint::CLOW].front();
         _q[Constraint::CLOW].pop_front();
         return c;
      }
   }
};

class CPSolver {
protected:
   Trailer::Ptr                  _sm;
   Storage::Ptr               _store;
   std::list<AVar::Ptr>       _iVars;
   DEPQueue                   _queue;
   std::list<std::function<void(void)>>  _onFix;
   long                  _afterClose;
   int                        _varId;
   unsigned long long  _propagations;
   size_t                    _nbProp;
   bool                   _inRestore;
   bool                 _inBranching;
public:
   template<typename T> friend class var;
   typedef handle_ptr<CPSolver> Ptr;
   CPSolver();
   ~CPSolver();
   Trailer::Ptr getStateManager()       { return _sm;}
   Storage::Ptr getStore()              { return _store;}
   unsigned long long getPropagations() {return _propagations;};
   size_t getNbVars() noexcept { return _iVars.size();}
   size_t getNbProp() noexcept { return _nbProp;}
    void registerVar(AVar::Ptr avar);
    void schedule(Constraint::Ptr& c) {
        if (c->isActive() && !c->isScheduled()) {
            c->setScheduled(true);
            _queue.enQueue(c);
        }
    }
    void onFixpoint(std::function<void(void)>& cb) { _onFix.emplace_back(cb);}
    void notifyFixpoint();
    void fixpoint();
    void post(Constraint::Ptr c,bool enforceFixPoint=true);
    void post(ConstraintDesc::Ptr c,bool enforceFixPoint=true);
    void startRestore() { _inRestore = true; }
    void endRestore() { _inRestore = false; }
    bool isInRestore() { return _inRestore; }
    void startBranching() { _inBranching = true; }
    void endBranching() { _inBranching = false; }
    bool isInBranching() { return _inBranching; }
    friend void* operator new(std::size_t sz,CPSolver::Ptr e);
    friend void* operator new[](std::size_t sz,CPSolver::Ptr e);
    friend std::ostream& operator<<(std::ostream& os,const CPSolver& s) {
       return os << "CPSolver(" << &s << ")" << std::endl;
    }
};

class CPSemSolver : public CPSolver {
    //MemoryTrail* _memoryTrail;
    Tracer* _tracer;
    bool _inSearch;
public:
    std::shared_ptr<Checkpoint> _rootCheckpoint;
    typedef handle_ptr<CPSemSolver> Ptr;
    CPSemSolver();
    ~CPSemSolver();
    void post(Constraint::Ptr c,bool enforceFixPoint=true);
    void post(ConstraintDesc::Ptr c,bool enforceFixPoint=true);
    Tracer* tracer();
    void startSearch();
};

namespace Factory {
   /**
    * Factory method to allocate a new CP solver.
    * @return a pointer to a solver.
    */
   inline CPSolver::Ptr makeSolver() { return new CPSolver;}
   inline CPSemSolver::Ptr makeSemSolver() { return new CPSemSolver;}
};

inline void* operator new(std::size_t sz,CPSolver::Ptr e)
{
   return e->_store->allocate(sz);
}

inline void* operator new[](std::size_t sz,CPSolver::Ptr e)
{
   return e->_store->allocate(sz);
}


#endif
