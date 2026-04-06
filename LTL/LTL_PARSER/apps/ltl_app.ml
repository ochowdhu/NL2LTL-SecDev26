(* 
open ltltutil.Ast
open ltlutil.ParserInterface 
*)

open Ast
open ParserInterface 


let rec repl _ = 
        print_string "$> "; 
        let input = read_line() in 
        let f = parse_formula input in 
        let result = formulaToString f in 
        print_endline result ; 
        print_endline "";
        repl() 


let _ = repl() 
