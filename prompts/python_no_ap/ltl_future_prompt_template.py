def generate_base_prompt(natural_language, atomic_propositions=None):
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
       

 You will follow the principle of maximal revelation — reveal as much logical structure 
as possible from the natural language description.

Your task has TWO parts:

## PART 1 — Extract Atomic Propositions
Identify all minimal, indivisible states or events in the text.
Assign each a short variable name: [a-zA-Z][a-zA-Z0-9]*
Output EXACTLY in this format:
<variable> : "<description of the state or event>"

## PART 2 — Generate LTL Formula  
Using ONLY the variable names you defined in Part 1, generate the LTL formula
as a single Python line using these constructors ONLY:
AtomicProposition, Eventually, Always, Next, Until, Since,
LAnd, LOr, LNot, LImplies, LEquiv

Output EXACTLY:
formulaToFind = <your formula>

Text:
"{natural_language}"

Stop after formulaToFind. No additional explanation.
"""

def generate_few_shot_examples():
    return """Here are examples of the exact format required:

Example 1:
Text: "It is always the case that if a request arrives a response will eventually follow"

auth : "request arrives"
resp : "response follows"
formulaToFind = Always(LImplies(AtomicProposition("auth"), Eventually(AtomicProposition("resp"))))

Example 2:
Text: "Eventually x will be true and then y will always hold after"

x : "x is true"
y : "y holds"
formulaToFind = Eventually(LAnd(AtomicProposition("x"), Always(AtomicProposition("y"))))

Now solve the following:
"""

def handle_self_refinement():
    return """
Please review your answer and refine if necessary.
Keep EXACTLY the same two-part format:
<variable> : "<description>"
formulaToFind = ...
No explanation.
"""

def generate_prompt(natural_language, atomic_propositions=None,
                    approach="zero_shot", initial_response=None):
    base = generate_base_prompt(natural_language)
    if approach == "zero_shot":
        return base
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            return base
        return f"Previous response:\n{initial_response}\n\n{handle_self_refinement()}\n\n{base}"
    elif approach == "few_shot":
        return generate_few_shot_examples() + "\n" + base
    else:
        raise ValueError(f"Unknown approach: {approach}")