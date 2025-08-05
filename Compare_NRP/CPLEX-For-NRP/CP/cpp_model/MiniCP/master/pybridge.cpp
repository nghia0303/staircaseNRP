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
 *
 * Contributions by Waldemar Cruz, Rebecca Gentzel, Willem Jan Van Hoeve
 */

#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

#include <sstream>
#include "store.hpp"
#include "solver.hpp"
#include "avar.hpp"
#include "intvar.hpp"
#include "acstr.hpp"
#include "matrix.hpp"
#include "constraint.hpp"
#include "search.hpp"

namespace py = pybind11;

PYBIND11_DECLARE_HOLDER_TYPE(T, handle_ptr<T>,true);
PYBIND11_MAKE_OPAQUE(Factory::Veci);
//PYBIND11_MAKE_OPAQUE(std::vector<var<int>::Ptr>);
                     
PYBIND11_MODULE(minicpp,m) {
   m.doc() = "MiniCPP Plugin for Python";

   //py::bind_vector<std::vector<var<int>::Ptr>>(m, "VectorVarInt");

   py::register_exception_translator([](std::exception_ptr p) {
                                        try {
                                           if (p) std::rethrow_exception(p);
                                        } catch (...) {
                                           PyErr_SetString(PyExc_RuntimeError, "FAIL");
                                        }
                                     });
   
   py::class_<Branches>(m,"Branches")
      .def(py::init<>())
      .def(py::init<std::function<void(void)>,std::function<void(void)>>(),py::keep_alive<1,2>());
   
   //py::class_<Chooser>(m,"Chooser");
   py::class_<AVar,AVar::Ptr>(m,"AVar");
   py::class_<Constraint,Constraint::Ptr>(m,"Constraint")
      .def("post",&Constraint::post)
      .def("propagate",&Constraint::propagate)
      .def("setSchedule",&Constraint::setScheduled)
      .def("isScheduled",&Constraint::isScheduled)
      .def("setActive",&Constraint::setActive)
      .def("isActive",&Constraint::isActive)
      .def("__repr__",[](const Constraint& s) {
                         std::ostringstream str;
                         s.print(str);
                         str << std::ends;
                         return str.str();
                      });

   py::class_<Objective,Objective::Ptr>(m,"Objective")
      .def("tighten",&Objective::tighten)
      .def("value",&Objective::value);

   py::class_<var<int>,AVar,var<int>::Ptr>(m,"VarInt")
      .def_property_readonly("min",&var<int>::min,"The smallest value in the domain")
      .def_property_readonly("max",&var<int>::max)
      .def_property_readonly("size",&var<int>::size)
      .def_property_readonly("isBound",&var<int>::isBound)
      .def("contains",&var<int>::contains)
      .def("assign",&var<int>::assign)
      .def("remove",&var<int>::remove)
      .def("removeBelow",&var<int>::removeBelow)
      .def("removeAbove",&var<int>::removeAbove)
      .def("updateBounds",&var<int>::updateBounds)
      .def("__neg__",[](const var<int>::Ptr& s)        { return Factory::operator-(s);},py::is_operator())
      .def("__mul__",[](const var<int>::Ptr& s,int a)  { return Factory::operator*(s,a);},py::is_operator())
      .def("__rmul__",[](const var<int>::Ptr& s,int a) { return Factory::operator*(s,a);},py::is_operator())
      .def("__add__",[](const var<int>::Ptr& s,int a)  { return Factory::operator+(s,a);},py::is_operator())
      .def("__radd__",[](const var<int>::Ptr& s,int a) { return Factory::operator+(s,a);},py::is_operator())
      .def("__sub__",[](const var<int>::Ptr& s,int a)  { return Factory::operator-(s,a);},py::is_operator())
      .def("__ne__",[](const var<int>::Ptr& a,const var<int>::Ptr& b) { return Factory::operator!=(a,b);},py::is_operator())
      .def("__eq__",[](const var<int>::Ptr& a,const var<int>::Ptr& b) { return Factory::equal(a,b,0);},py::is_operator())
      .def("__ne__",[](const var<int>::Ptr& a,int b) {
         TRYFAIL {
            return Factory::operator!=(a,b);
         } ONFAIL {
            //std::cout << "failure in x!=" << b << std::endl;
            throw Failure; // convert longjmp/setjmp back to C++ exception to go through pybind layer
         } ENDFAIL
      },py::is_operator())
      .def("__eq__",[](const var<int>::Ptr& a,int b) {
         TRYFAIL {
            return Factory::operator==(a,b);
         } ONFAIL {
            //std::cout << "failure in x==" << b << std::endl;
            throw Failure; // convert longjmp/setjmp back to C++ exception to go through pybind layer
         } ENDFAIL
      },py::is_operator())
      .def("__le__",[](const var<int>::Ptr& a,const var<int>::Ptr& b) { return Factory::operator<=(a,b);},py::is_operator())
      .def("__ge__",[](const var<int>::Ptr& a,const var<int>::Ptr& b) { return Factory::operator>=(a,b);},py::is_operator())
      .def("__le__",[](const var<int>::Ptr& a,int b) { return Factory::operator<=(a,b);},py::is_operator())
      .def("__ge__",[](const var<int>::Ptr& a,int b) { return Factory::operator>=(a,b);},py::is_operator())
      .def("__repr__",[](const var<int>& s) {
                         std::ostringstream str;
                         s.print(str);
                         str << std::ends;
                         return str.str();
                      });
   py::class_<var<bool>,AVar,var<bool>::Ptr>(m,"VarBool")
      .def(py::init<CPSolver::Ptr&>())
      .def("isTrue",&var<bool>::isTrue)
      .def("isFalse",&var<bool>::isFalse)
      .def("assign",&var<bool>::assign)
      .def("__repr__",[](const var<bool>& s) {
                         std::ostringstream str;
                         s.print(str);
                         str << std::ends;
                         return str.str();
                      });

   
   py::class_<CPSolver,CPSolver::Ptr>(m,"CPSolver")
      .def("fixpoint",&CPSolver::fixpoint)
      .def("post",[](CPSolver::Ptr cp,Constraint::Ptr c,bool enforceFixPoint) {
         TRYFAIL {
            cp->post(c,enforceFixPoint);
         } ONFAIL {
            std::cout << "failure caught ..." << std::endl;            
         } ENDFAIL         
      },
         py::arg("c"),
         py::arg("enforceFixPoint")=true,
         "Post the constraint `c` and runs the fixpoint as required.")
      .def("__repr__",[](const CPSolver& s) {
                         std::ostringstream str;
                         str << s << std::ends;
                         return str.str();
                      });

   py::class_<Storage,Storage::Ptr>(m,"Storage");
   py::class_<stl::StackAdapter<var<int>::Ptr,Storage::Ptr>>(m,"Alloci");
   py::class_<EVec<var<int>::Ptr,stl::StackAdapter<var<int>::Ptr,Storage::Ptr>>>(m,"VecIntVar")
      .def("__getitem__",[](const Factory::Veci& s,size_t i) { return s[i];})
      .def("__setitem__",[](Factory::Veci& s,size_t i,var<int>::Ptr e) { s[i] = e;})
      .def("__len__",[](const Factory::Veci& s) { return s.size();})
      .def("__iter__",[](const Factory::Veci& s) { return py::make_iterator(s.begin(),s.end());},py::keep_alive<0,1>())
      .def("__repr__",[](const Factory::Veci& s) {
                         std::ostringstream str;
                         str << s << std::ends;
                         return str.str();
                      });
   py::class_<EVec<var<bool>::Ptr,stl::StackAdapter<var<bool>::Ptr,Storage::Ptr>>>(m,"VecBoolVar")
      .def("__getitem__",[](const Factory::Vecb& s,size_t i) { return s[i];})
      .def("__setitem__",[](Factory::Vecb& s,size_t i,var<bool>::Ptr e) { s[i] = e;})
      .def("__len__",[](const Factory::Vecb& s) { return s.size();})
      .def("__iter__",[](const Factory::Vecb& s) { return py::make_iterator(s.begin(),s.end());},py::keep_alive<0,1>())
      .def("__repr__",[](const Factory::Vecb& s) {
                         std::ostringstream str;
                         str << s << std::ends;
                         return str.str();
                      });

   py::class_<SearchStatistics>(m,"SearchStatistics")
      .def(py::init<>())
      .def("incrFailures",&SearchStatistics::incrFailures)
      .def("incrNodes",&SearchStatistics::incrNodes)
      .def("incrSolutions",&SearchStatistics::incrSolutions)
      .def("setNotCompleted",&SearchStatistics::setNotCompleted)
      .def("numberOfFailures",&SearchStatistics::numberOfFailures)
      .def("numberOfNodes",&SearchStatistics::numberOfNodes)
      .def("numberOfSolutions",&SearchStatistics::numberOfSolutions)
      .def("getCompleted",&SearchStatistics::getCompleted)
      .def("__repr__",[](const SearchStatistics& s) {
                         std::ostringstream str;
                         str << s << std::ends;
                         return str.str();
                      });      
      
   py::class_<DFSearch>(m,"DFSearch")
      .def(py::init<CPSolver::Ptr,std::function<Branches(void)>>())
      .def("onSolution",&DFSearch::onSolution<std::function<void(void)>>)
      .def("onFailure",&DFSearch::onFailure<std::function<void(void)>>)
      .def("solve",py::overload_cast<>(&DFSearch::solve))
      .def("solve",py::overload_cast<std::function<bool(const SearchStatistics&)>>(&DFSearch::solve))
      // .def("solve",[](DFSearch& s,std::function<bool(const SearchStatistics&)> lim) {
      //    auto stat = s.solve(lim); // this was for debugging purposes.
      //    return stat;
      // })
      .def("solve",py::overload_cast<SearchStatistics&,std::function<bool(const SearchStatistics&)>>(&DFSearch::solve))
      .def("solveSubjectTo",&DFSearch::solveSubjectTo)
      .def("optimize",py::overload_cast<Objective::Ptr>(&DFSearch::optimize))
      .def("optimize",py::overload_cast<Objective::Ptr,std::function<bool(const SearchStatistics&)>>(&DFSearch::optimize))
      .def("optimizeSubjectTo",&DFSearch::optimizeSubjectTo)
      ;
   
   
   m.def("makeSolver",&Factory::makeSolver,"factory method");
   m.def("makeIntVar",py::overload_cast<CPSolver::Ptr,int,int>(&Factory::makeIntVar),"factory method");
   m.def("makeBoolVar",py::overload_cast<CPSolver::Ptr>(&Factory::makeBoolVar),"factory for boolean variables");
   m.def("intVarArray",(Factory::Veci (*)(CPSolver::Ptr,int,int,int))(&Factory::intVarArray),"factory method var<int>[]");
   m.def("intVarArray",(Factory::Veci (*)(CPSolver::Ptr,int,int))(&Factory::intVarArray),"factory method var<int>[]");
   m.def("intVarArray",(Factory::Veci (*)(CPSolver::Ptr,int))(&Factory::intVarArray),"factory method var<int>[]");
   m.def("boolVarArray",(Factory::Vecb (*)(CPSolver::Ptr,int,bool))(&Factory::boolVarArray),"factory method var<bool>[]");

   m.def("equal",py::overload_cast<var<int>::Ptr,var<int>::Ptr,int>(&Factory::equal));
   m.def("notEqual",&Factory::notEqual);
   m.def("isEqual",&Factory::isEqual);
   m.def("isLarger",&Factory::isLarger);
   m.def("isLess",&Factory::isLess);
   m.def("isLessOrEqual",&Factory::isLessOrEqual);
   m.def("isLargerOrEqual",&Factory::isLargerOrEqual);
   
   m.def("sum",static_cast<Constraint::Ptr (*)(const Factory::Veci&,var<int>::Ptr)>(&Factory::sum));
   m.def("sum",static_cast<Constraint::Ptr (*)(const std::vector<var<int>::Ptr>&,var<int>::Ptr)>(&Factory::sum));
   m.def("sum",static_cast<Constraint::Ptr (*)(const std::vector<var<bool>::Ptr>&,var<int>::Ptr)>(&Factory::sum));
   m.def("sum",static_cast<Constraint::Ptr (*)(const std::vector<var<int>::Ptr>&,int)>(&Factory::sum));
   m.def("sum",static_cast<Constraint::Ptr (*)(const std::vector<var<bool>::Ptr>&,int)>(&Factory::sum));
   m.def("sum",static_cast<var<int>::Ptr (*)(Factory::Veci&)>(&Factory::sum<Factory::Veci>));
   m.def("sum",static_cast<var<int>::Ptr (*)(std::vector<var<int>::Ptr>&)>(&Factory::sum<std::vector<var<int>::Ptr>>));
   
   m.def("allDifferent",&Factory::allDifferent<std::vector<var<int>::Ptr>>);
   m.def("allDifferentAC",&Factory::allDifferentAC<std::vector<var<int>::Ptr>>);
   m.def("circuit",&Factory::circuit<std::vector<var<int>::Ptr>>);
   m.def("clause",&Factory::clause<std::vector<var<bool>::Ptr>>);
   m.def("element",py::overload_cast<const std::vector<int>&,var<int>::Ptr,var<int>::Ptr>(&Factory::element<std::vector<int>>));
   m.def("element",[](const std::vector<std::vector<int>>& mat,var<int>::Ptr x,var<int>::Ptr y) {
                      Matrix<int,2> d({(int) mat.size(),(int) mat.front().size()});
                      for(auto i = 0u ; i < mat.size();i++)
                         for(auto j = 0u; j < mat[i].size();j++)
                            d[i][j] = mat[i][j];
                      return Factory::element(d,x,y);
                   });
   m.def("minimize",&Factory::minimize);
   
   m.def("firstFail",&firstFail<Factory::Veci>);
   m.def("firstFail",&firstFail<std::vector<var<int>::Ptr>>);
   m.def("DFFFail",[](CPSolver::Ptr cp,const Factory::Veci& vars) {
                      DFSearch search(cp,firstFail(cp,vars));
                      return search;
                   });
   using FVInt2Bool = std::function<bool(var<int>::Ptr)>;
   using FVInt2Int  = std::function<int(var<int>::Ptr)>;
   m.def("selectMin",static_cast<var<int>::Ptr (*)(const Factory::Veci&,FVInt2Bool,FVInt2Int)>(&selectMin3));
   m.def("indomain_min",static_cast<Branches (*)(CPSolver::Ptr,var<int>::Ptr)>(&indomain_min));
   m.def("indomain_max",static_cast<Branches (*)(CPSolver::Ptr,var<int>::Ptr)>(&indomain_max));
}
