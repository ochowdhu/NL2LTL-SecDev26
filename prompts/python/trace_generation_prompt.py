def generate_base_prompt(ltl_formula: str) -> str:
    return f'''You are an expert in Python 3. Your task is to determine a value for the variable `traceGivenAsInput` such that the function prints **POSITIVE** (i.e., the formula evaluates to True) and also such that it prints **NEGATIVE** (i.e., the formula evaluates to False).

```python
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
            return ReallyNone()

formulaToFind = {ltl_formula}
traceGivenAsInput = ___FILL_THIS___

result = evalFormula(formulaToFind, traceGivenAsInput, 0)

match result:
    case Some(True): print("POSITIVE")
    case Some(False): print("NEGATIVE")
    case _: print("UNKNOWN")
    ```

**STRICTLY** Return your answer as a valid string representing a list of states, formatted as:
SATISFYING: [x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE] FALSIFYING: [x1 = TRUE, x2 = TRUE];[x1 = TRUE, x2 = FALSE]
**NO ADDITIONAL TEXT OR PYTHON LIST LITERALS SHOULD BE GIVEN, JUST THE TRACE STRING GENERATED**
'''

def generate_few_shot_prompt(ltl_formula: str) -> str:
    # Add examples before the base prompt
    examples = '''Here are some examples of how to solve similar problems:

Example 1:
LTL Formula: Always(LImplies(AtomicProposition("a"), Eventually(AtomicProposition("b"))))
SATISFYING: [a = FALSE, b = FALSE];[a = TRUE, b = FALSE];[a = FALSE, b = TRUE]
FALSIFYING: [a = TRUE, b = FALSE];[a = TRUE, b = FALSE];[a = TRUE, b = FALSE]

Example 2:
LTL Formula: Eventually(LAnd(AtomicProposition("a"), AtomicProposition("b")))
SATISFYING: [a = FALSE, b = TRUE];[a = TRUE, b = FALSE];[a = TRUE, b = TRUE]
FALSIFYING: [a = FALSE, b = FALSE];[a = FALSE, b = FALSE];[a = FALSE, b = FALSE]

Now solve the following problem:

'''
    
    # Get the base prompt and prepend the examples
    base_prompt = generate_base_prompt(ltl_formula)
    return examples + base_prompt

def handle_self_refinement(base_prompt: str, initial_response: str) -> str:

    return f'''{base_prompt}

    Your initial response was:

    {initial_response}
    If necessary, revise your answer to ensure:

    - The trace format is strictly: [x1 = TRUE, x2 = FALSE];...

    - Both positive and negative traces are included

    - No explanation is provided

    Return only the corrected positive and negative trace.

    **NO ADDITIONAL TEXT SHOULD BE GIVEN**

    '''

def generate_prompt(formula, approach, initial_response=None):
    if approach == "zero_shot":
        return generate_base_prompt(formula)
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            raise ValueError("Initial response is required for zero-shot self-refinement")
        return handle_self_refinement(generate_base_prompt(formula), initial_response)

    elif approach == "few_shot":
        return generate_few_shot_prompt(formula)  # Pass the formula here!

    else:
        raise ValueError(f"Unknown approach: {approach}")
