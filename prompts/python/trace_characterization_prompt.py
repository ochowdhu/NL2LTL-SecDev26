def generate_base_prompt(ltl_formula: str, trace: str) -> str:
    return f'''You are an expert in Python3 and temporal logic.
You are given an LTL formula represented as Python classes and a trace represented as a list of states.
Your task is to evaluate whether the formula holds over the trace starting at position 0.

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
            return ReallyNone()`

# Evaluate the following formula on the trace:
formulaToFind = {ltl_formula}
traceGivenAsInput = {trace}

result = evalFormula(formulaToFind, traceGivenAsInput, 0)

match result:
    case Some(True): print("POSITIVE")
    case Some(False): print("NEGATIVE")
    case _: print("UNKNOWN")```

NO ADDITIONAL EXPLANATION IS NEEDED, just provide a POSITIVE, NEGATIVE, or UNKNOWN response
'''

def handle_self_refinement(base_prompt: str, initial_response: str) -> str:
    return f'''{base_prompt}

Your initial response was: {initial_response}

Please carefully review your initial analysis using the Python3 temporal logic evaluator and consider the following:
1. Did you properly convert the trace format to the internal representation?
2. Did you correctly trace through the evalFormula function execution?

NO ADDITIONAL EXPLANATION SHOULD BE GIVEN, just provide a POSITIVE, NEGATIVE, or UNKNOWN.
'''

def generate_few_shot_prompt(ltl_formula: str, trace: str) -> str:
    return f'''Here are some examples:

Example 1:
LTL Formula: Eventually(AtomicProposition("x1"))
Trace: [[("x1", False)], [("x1", False)], [("x1", True)], [("x1", True)]]
Answer: POSITIVE

Example 2:
LTL Formula: Eventually(AtomicProposition("x1"))
Trace: [[("x1", False)], [("x1", False)], [("x1", False)]]
Answer: NEGATIVE

Example 3:
LTL Formula: Always(LImplies(AtomicProposition("x1"), AtomicProposition("x2")))
Trace: [[("x1", True), ("x2", True)], [("x1", True), ("x2", False)]]
Answer: NEGATIVE

Now evaluate:
LTL Formula: {ltl_formula}
Trace: {trace}
NO ADDITIONAL CODE IS NEEDED, just provide a POSITIVE, NEGATIVE, or UNKNOWN response.
Answer:
'''

def generate_prompt(ltl_formula: str, trace: str, approach: str, initial_response: str = None) -> str:
    if approach == "zero_shot":
        return generate_base_prompt(ltl_formula, trace)
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            raise ValueError("Initial response is required for zero-shot self-refinement")
        return handle_self_refinement(generate_base_prompt(ltl_formula, trace), initial_response)

    elif approach == "few_shot":
        return generate_few_shot_prompt(ltl_formula, trace)

    else:
        raise ValueError(f"Unknown approach: {approach}")
