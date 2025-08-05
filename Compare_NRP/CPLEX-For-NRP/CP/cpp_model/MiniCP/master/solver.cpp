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
#include <assert.h>
#include <iostream>
#include <iomanip>
#include <typeindex>
#include "tracer.hpp"

CPSolver::CPSolver()
    : _sm(new Trailer),
      _store(new Storage(_sm))
{
    _varId  = 0;
    _propagations = 0;
    _nbProp = 0;
}

CPSolver::~CPSolver()
{
   _iVars.clear();
   _store.dealloc();
   _sm.dealloc();
   std::cout << "CPSolver::~CPSolver(" << this << ")" << std::endl;
}

void CPSolver::post(Constraint::Ptr c, bool enforceFixPoint)
{
   if (!c)
      return;
   ++_nbProp;
   c->post();
   if (enforceFixPoint)
      fixpoint();
}

void CPSolver::post(ConstraintDesc::Ptr c, bool enforceFixPoint)
{
   if (!c)
      return;
   ++_nbProp;
   auto constraint = c->create();
   constraint->post();
   if (enforceFixPoint)
      fixpoint();
}

void CPSolver::registerVar(AVar::Ptr avar)
{
   avar->setId(_varId++);
   _iVars.push_back(avar);
}

void CPSolver::notifyFixpoint()
{
   for(auto& body : _onFix)
      body();
}

void CPSolver::fixpoint()
{
   TRYFAIL
      notifyFixpoint();
      while (!_queue.empty()) {
         auto c = _queue.deQueue();
         c->setScheduled(false);
         if (c->isActive())
         {
             c->propagate();
             _propagations += 1;
         }
      }
      assert(_queue.size() == 0);
   ONFAIL
      while (!_queue.empty()) {
         _queue.deQueue()->setScheduled(false);
      }
      assert(_queue.size() == 0);
      failNow();
   ENDFAIL
}


CPSemSolver::CPSemSolver()
   : _tracer(new Tracer(_sm)),
     _inSearch(false) { }

CPSemSolver::~CPSemSolver()
{
   delete _tracer;
}

//If it calls post with a constraint, we trust that this is not in the search, and so we don't need to add it to the memoryTrail
void CPSemSolver::post(Constraint::Ptr c, bool enforceFixPoint)
{
   if (!c)
      return;
   ++_nbProp;
   c->post();
   if (enforceFixPoint)
      fixpoint();
}
void CPSemSolver::post(ConstraintDesc::Ptr c, bool enforceFixPoint)
{
   if (!c)
      return;
   ++_nbProp;
   if (_inSearch) {
      auto saved = c->clone();
      _tracer->addCommand(saved);
   }
   auto constraint = c->create();
   constraint->post();
   if (enforceFixPoint)
      fixpoint();
}
Tracer* CPSemSolver::tracer()
{
   return _tracer;
}
void CPSemSolver::startSearch()
{
   _inSearch = true;
   _rootCheckpoint = _tracer->captureCheckpoint();
   _tracer->restoreCheckpoint(_rootCheckpoint,this);
   //Restore immediately otherwise will have an empty list at the start which we don't really want
}
