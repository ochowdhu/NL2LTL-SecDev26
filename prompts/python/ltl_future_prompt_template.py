def generate_base_prompt(natural_language, atomic_propositions):
    return f"""
You are a teacher who is proficient in propositional linear temporal logic (LTL) and Python.

You are given the following Python class structure that defines how LTL formulas should be represented:

```python
from dataclasses import dataclass
from typing import *

class Formula:
    pass

@dataclass
class AtomicProposition(Formula):
    name : str

@dataclass
class Literal(Formula):
    name : str

@dataclass
class LNot(Formula):
    Formula: Formula

@dataclass
class LAnd(Formula):
    left: Formula
    right: Formula

@dataclass
class LOr(Formula):
    left: Formula
    right: Formula

@dataclass
class LImplies(Formula):
    left: Formula
    right: Formula

@dataclass
class LEquiv(Formula):
    left: Formula
    right: Formula    

@dataclass
class Since(Formula):
    a : Formula
    b : Formula

@dataclass
class Until(Formula):
    a : Formula
    b : Formula    

@dataclass
class Next(Formula):
    Formula: Formula  

@dataclass
class Always(Formula):
    Formula: Formula

@dataclass
class Eventually(Formula):
    Formula: Formula

@dataclass
class Once(Formula):
    Formula: Formula

@dataclass
class Historically(Formula):
    Formula: Formula

@dataclass
class Yesterday(Formula):
    Formula: Formula


FormulaType = Union[AtomicProposition, Literal, LNot, LAnd, LOr, LImplies, LEquiv, Since, Until, Next, Always, Eventually, Once, Historically, Yesterday]    

type varToValMapping = tuple[str, bool]
type state = list[varToValMapping]
type trace = list[state]

class OptionType:
    pass

@dataclass
class ReallyNone(OptionType):
    pass

@dataclass
class Some(OptionType):
    value: bool

myOptionType = Union[ReallyNone, Some]  

def isPropositionTrueInTracePosition(p : AtomicProposition, t: trace, pos: int) -> myOptionType:
    if pos < 0 or pos >= len(t):
        return ReallyNone()
    state_at_pos = t[pos]
    for var, val in state_at_pos:
        if var == p.name:
            return Some(val)
    return ReallyNone()

def evalFormula(f : Formula, t: trace, pos: int) -> myOptionType:
    match f:
        case AtomicProposition(name):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            return isPropositionTrueInTracePosition(f, t, pos)
        case Literal(name):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            if name == "True":
                return Some(True)
            elif name == "False":
                return Some(False)
            else:
                return ReallyNone()
        case LNot(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            inner_eval = evalFormula(inner, t, pos)
            match inner_eval:
                case Some(val):
                    return Some(not val)
                case ReallyNone():
                    return ReallyNone()
        case LAnd(left, right):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            left_eval = evalFormula(left, t, pos)
            right_eval = evalFormula(right, t, pos)
            match left_eval, right_eval:
                case (Some(lval), Some(rval)):
                    return Some(lval and rval)
                case (ReallyNone(), _):
                    return ReallyNone()
                case (_, ReallyNone()):
                    return ReallyNone()
        case LOr(left, right):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            left_eval = evalFormula(left, t, pos)
            right_eval = evalFormula(right, t, pos)
            match left_eval, right_eval:
                case (Some(lval), Some(rval)):
                    return Some(lval or rval)
                case (ReallyNone(), _):
                    return ReallyNone()
                case (_, ReallyNone()):
                    return ReallyNone()
        case LImplies(left, right):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            left_eval = evalFormula(left, t, pos)
            right_eval = evalFormula(right, t, pos)
            match left_eval, right_eval:
                case (Some(lval), Some(rval)):
                    return Some((not lval) or rval)
                case (ReallyNone(), _):
                    return ReallyNone()
                case (_, ReallyNone()):
                    return ReallyNone()
        case LEquiv(left, right):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            left_eval = evalFormula(left, t, pos)
            right_eval = evalFormula(right, t, pos)
            match left_eval, right_eval:
                case (Some(lval), Some(rval)):
                    return Some(lval == rval)
                case (ReallyNone(), _):
                    return ReallyNone()
                case (_, ReallyNone()):
                    return ReallyNone()
        case Since(a, b):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            foundB = False
            i = pos
            while i >= 0 :
                eval_result = evalFormula(b, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and eval_result.value:
                    foundB = True
                    break
                i -= 1
            if not foundB:
                return Some(False)
            j = i + 1
            while j <= pos:  
                eval_result = evalFormula(a, t, j)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and not eval_result.value:
                    return Some(False)
                j += 1      
            return Some(True)    
        case Until(a, b):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            foundB = False
            i = pos
            while i < len(t) :
                eval_result = evalFormula(b, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and eval_result.value:
                    foundB = True
                    break
                i += 1
            if not foundB:
                return Some(False)
            j = pos
            while j < i:  
                eval_result = evalFormula(a, t, j)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and not eval_result.value:
                    return Some(False)
                j += 1      
            return Some(True)    

        case Next(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            if pos + 1 < len(t):
                return evalFormula(inner, t, pos + 1)
            else:
                return ReallyNone()
        case Always(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            for i in range(pos, len(t)):
                eval_result = evalFormula(inner, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and not eval_result.value:
                    return Some(False)
            return Some(True)
        case Eventually(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            for i in range(pos, len(t)):
                eval_result = evalFormula(inner, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and eval_result.value:
                    return Some(True)
            return Some(False)
        case Once(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            for i in range(0, pos+1):
                eval_result = evalFormula(inner, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and eval_result.value:
                    return Some(True)
            return Some(False)
        case Historically(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            for i in range(0, pos+1):
                eval_result = evalFormula(inner, t, i)
                if isinstance(eval_result, ReallyNone):
                    return ReallyNone()
                if isinstance(eval_result, Some) and not eval_result.value:
                    return Some(False)
            return Some(True)
        case Yesterday(inner):
            if pos < 0 or pos >= len(t):
                return ReallyNone()
            if pos >= 1:
                return evalFormula(inner, t, pos - 1)
            else:
                return Some(False)
        case _:
            return ReallyNone()```
       

  Your task is to fill up the value of the 
variable formulaToFind in the code such that 
if the user chooses a value for traceGivenAsInput,
the program will print "TRUE" if and only if the 
user-chosen value for traceGivenAsInput satisfies the formula. 

For choosing the value for `formulaToFind`, you are given the 
following natural language description along with a mapping from 
natural language fragment to variable names to use. 

You should restrict yourself to only using those variable names 
given to you in the mapping, and nothing else.

Input:
 Natural Language: "{natural_language}"
 Atomic Propositions: {atomic_propositions}

 You MUST use ONLY the Python class constructors provided below 
(AtomicProposition, Eventually, Always, LAnd, LOr, LNot, LImplies, LEquiv, Next, Until). 
You MUST only use the variables provided in the Atomic Propositions mapping.

You MUST return ONLY a single line of valid Python code like this
formulaToFind = <your formula here>
"""

def handle_self_refinement():
    """Generate refinement prompt"""
    return """
Please review your answer refine it if necessary with NO EXPLANATION.
"""

def generate_few_shot_examples():
    """Generate few-shot examples"""
    return """Here are some examples of natural language to temporal logic translation:

Example 1:
Natural Language: "It is always the case that either the door is open or the window is open"
Atomic Propositions: door_open : p, window_open : q
formulaToFind = Always(LOr(AtomicProposition("p"), AtomicProposition("q")))

Example 2:
Natural Language: "Eventually x will be true"
Atomic Propositions: x : x
formulaToFind = Eventually(AtomicProposition("x"))

Example 3:
Natural Language: "If x is true, then y will be true in the next state"
Atomic Propositions: x : x, y : y
formulaToFind = Always(LImplies(AtomicProposition("x"), Next(AtomicProposition("y"))))

Now solve the following:
"""

def generate_prompt(nl_statement, atomic_propositions, approach, initial_response=None):
    """Generate prompt based on approach"""
    base_prompt = generate_base_prompt(nl_statement, atomic_propositions)
    
    if approach == "zero_shot":
        return base_prompt
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            return base_prompt
        else:
            refinement_prompt = handle_self_refinement()
            return f"Previous response: {initial_response}\n\n{refinement_prompt}\n\n{base_prompt}"
    elif approach == "few_shot":
        few_shot_examples = generate_few_shot_examples()
        return few_shot_examples + "\n" + base_prompt
    else:
        raise ValueError(f"Unknown approach: {approach}")