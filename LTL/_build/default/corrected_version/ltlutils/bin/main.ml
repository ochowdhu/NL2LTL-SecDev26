open Ltlutils

type tracegen = POSITIVE_TRACE_GEN | NEGATIVE_TRACE_GEN

(* "/Users/omar/Documents/SOFTWARE/MODEL-CHECKER/WORKING-NuSMV-2.6.0-Darwin/bin/" *)

let nusmv_executable_full_path = 
        let nusmv_path = Sys.getenv_opt "NUSMVBINPATH" in 
        match nusmv_path with 
        | Some(s) -> 
          (* let () = Printf.eprintf "Found NUSMVBINPATH in: %s\n\n" s in  *)
        s 
        | None -> "/usr/local/bin"

let print_set_debugging s = 
  Utilfuncs.StringSet.iter (fun x -> Printf.eprintf "%s " x) s  ; 
  Printf.eprintf "\n" 

(* let nusmv_exe = String.cat nusmv_executable_full_path "NuSMV"
let get_file_full_path s = String.cat nusmv_executable_full_path s *)

let nusmv_exe = String.cat nusmv_executable_full_path "/nusmv"
let get_file_full_path s = Filename.concat (Filename.get_temp_dir_name ()) s

let check_past _ =
  let raw_line = read_line () in
  let f = Parserinterface.parse_formula raw_line in
  let result = Utilfuncs.is_past_temporal_formula f in
  if result = true then
    let () = Printf.printf "Yes" in  
    (Printf.eprintf "Yes!! Formula %s contains only past temporal operators\n\n"
      (Ast.formulaToString f))
  else
    let () = Printf.printf "No" in 
    Printf.eprintf
      "No!! Formula %s does **not** contain only past temporal operators\n\n"
      (Ast.formulaToString f)

let formulas_are_meaningfully_comparable varf1 varf2 =
  Utilfuncs.StringSet.equal varf1 varf2
  || Utilfuncs.StringSet.subset varf1 varf2
  || Utilfuncs.StringSet.subset varf1 varf2

(* let get_result output_filename =  *)

let get_result_from_file (positive_message : string) (negative_message : string)
    =
  let ic =
    open_in (get_file_full_path "query_result.out")
    (* (Ast.convert_string_list_to_one_string [nusmv_executable_full_path; "query_result.out"])  *)
  in
  try
    let line = input_line ic in
    let () = close_in_noerr ic in 
    if String.equal (String.trim line) "true" then
      Printf.printf "%s\n%!" positive_message
    else Printf.printf "%s\n%!" negative_message
  with e ->
    Printf.eprintf "%s\n%!" "Result file not found";
    close_in_noerr ic;
    raise e
(* ; Printf.printf "%s\n" "Result file not found"         *)

let run_equiv_command f1 f2 : unit =
  let query = Nusmvconnect.generate_equivalence_query true f1 f2 in
  let qfile = get_file_full_path "query.smv" in
  let cmd_to_run =
    Ast.convert_string_list_to_one_string
      [
        nusmv_exe;
        " -dcx ";
        qfile;
        " | grep '^--' | grep -oE '[^ ]+$'  &>  ";
        get_file_full_path "query_result.out";
      ]
  in
  let oc = open_out qfile in
  Printf.fprintf oc "%s\n%!" query;
  let () = close_out_noerr oc in 
  if Sys.command cmd_to_run = 0 then
    Printf.eprintf "%s\n" (String.cat cmd_to_run " : [Ran Successfully] \n\n")
  else
    Printf.eprintf "%s\n" 
      (String.cat cmd_to_run
         " : [Didn't run successfully] *** RESULT NOT MEANINGFUL ***\n\n")

let run_entailment_command f1 f2 : unit =
  let query = Nusmvconnect.generate_equivalence_query false f1 f2 in
  let qfile = get_file_full_path "query.smv" in
  let cmd_to_run =
    Ast.convert_string_list_to_one_string
      [
        nusmv_exe;
        " -dcx ";
        qfile;
        " | grep '^--' | grep -oE '[^ ]+$'  &>  ";
        get_file_full_path "query_result.out";
      ]
  in
  let oc = open_out qfile in
  Printf.fprintf oc "%s\n%!" query;
  let () = close_out_noerr oc in 
  if Sys.command cmd_to_run = 0 then
    Printf.eprintf "%s\n" (String.cat cmd_to_run " : [Ran Successfully] \n\n")
  else
    Printf.eprintf "%s\n" 
      (String.cat cmd_to_run
         " : [Didn't run successfully] *** RESULT NOT MEANINGFUL ***\n\n")


let check_equiv _ =
  let raw_line_f1 = read_line () in
  let raw_line_f2 = read_line () in
  let f1 = Parserinterface.parse_formula raw_line_f1 in
  let f2 = Parserinterface.parse_formula raw_line_f2 in
  let varf1 = Utilfuncs.get_prop_vars_from_formula f1 in
  let varf2 = Utilfuncs.get_prop_vars_from_formula f2 in
  if formulas_are_meaningfully_comparable varf1 varf2 then
    let () = run_equiv_command f1 f2 in
    get_result_from_file "EQUIVALENT"
      "NOT_EQUIVALENT"
  else Printf.printf "NOT_MEANINGFUL"

  let check_entailment _ =
    let raw_line_f1 = read_line () in
    let raw_line_f2 = read_line () in
    let f1 = Parserinterface.parse_formula raw_line_f1 in
    let f2 = Parserinterface.parse_formula raw_line_f2 in
    let varf1 = Utilfuncs.get_prop_vars_from_formula f1 in
    let varf2 = Utilfuncs.get_prop_vars_from_formula f2 in
    if formulas_are_meaningfully_comparable varf1 varf2 then
      let () = run_entailment_command f1 f2 in
      get_result_from_file "Yes"
        "No"
    else Printf.printf "NOT_MEANINGFUL"
  

let run_trace_gen command f output_file_name =
  let query =
    if command = NEGATIVE_TRACE_GEN then
      Nusmvconnect.generate_negative_trace_query f
    else Nusmvconnect.generate_positive_trace_query f
  in
  let qfile = get_file_full_path "query.smv" in
  let cmd_to_run =
    Ast.convert_string_list_to_one_string
      [
        nusmv_exe;
        "  ";
        qfile;
        " | grep '^--' | grep -oE '[^ ]+$'  &>  ";
        get_file_full_path "query_result.out";
      ]
  in
  let oc = open_out qfile in
  Printf.fprintf oc "%s\n%!" query;
  let () = close_out_noerr oc in 
  if Sys.command cmd_to_run = 0 then
    let () =
      print_string (String.cat cmd_to_run " : [Ran Successfully] \n\n")
    in
    let full_cmd =
      Ast.convert_string_list_to_one_string
        [ nusmv_exe; "  "; qfile; "  >  "; get_file_full_path output_file_name ]
    in
    let scode = Sys.command full_cmd in
    if scode = 0 then print_string "Second run successful\n"
    else print_string "Second run *** unsuccessful ***\n"
  else
    print_string
      (String.cat cmd_to_run
         " : [Didn't run successfully] *** RESULT NOT MEANINGFUL ***\n\n");
  ()

let negative_trace_gen _ =
  let raw_line_f1 = read_line () in
  let output_file_name = read_line () in
  let f1 = Parserinterface.parse_formula raw_line_f1 in
  let () = run_trace_gen NEGATIVE_TRACE_GEN f1 (String.cat "negative-" (String.trim output_file_name)) in
  get_result_from_file
    "THE FORMULA IS TAUTOLOGICAL AND HENCE DO NOT HAVE ANY NEGATIVE TRACES"
    (String.cat "NEGATIVE TRACE GENERATED SUCCESSFULLY and CAN BE FOUND IN THE FOLLOWING LOCATION:\n"
    (get_file_full_path (String.cat "negative-" (String.trim output_file_name)) ))

let positive_trace_gen _ =
  let raw_line_f1 = read_line () in
  let output_file_name = read_line () in
  let f1 = Parserinterface.parse_formula raw_line_f1 in
  let () = run_trace_gen POSITIVE_TRACE_GEN f1 (String.cat "positive-" (String.trim output_file_name)) in
  get_result_from_file
    "THE FORMULA IS UNSATISFIABLE AND HENCE DO NOT HAVE ANY POSITIVE TRACES"
    (String.cat "POSITIVE TRACE GENERATED SUCCESSFULLY and CAN BE FOUND IN THE FOLLOWING LOCATION:\n"
    (get_file_full_path (String.cat "negative-" (String.trim output_file_name)) ))

let check_future _ =
  let raw_line = read_line () in
  let f = Parserinterface.parse_formula raw_line in
  let result = Utilfuncs.is_future_temporal_formula f in
  if result = true then
    let () = Printf.printf "Yes" in 
    Printf.eprintf "Yes!! Formula %s contains only future temporal operators\n\n"
      (Ast.formulaToString f)
  else
    let () = Printf.printf "No" in 
    Printf.eprintf
      "No!! Formula %s does **not** contain only future temporal operators\n\n"
      (Ast.formulaToString f)


let check_trace_satisfaction _ = 
  let raw_formula_string = read_line() in 
  let f = Parserinterface.parse_formula raw_formula_string in 
  let raw_trace_string = read_line() in 
  let ttrace = Traceparserinterface.parse raw_trace_string in 
  let cresult = Traceast.is_trace_consistent ttrace in 
  let () = Traceast.print_trace ttrace in let () = Printf.eprintf "%s\n" (Ast.formulaToString f) in 
  if cresult then 
    let vlistfromctrace = Traceast.get_variables_from_consistent_trace ttrace in 
    let vlistfromformula = Utilfuncs.get_prop_vars_from_formula f in 
    let () = print_set_debugging vlistfromctrace in 
    let () = print_set_debugging vlistfromformula in 
    if Utilfuncs.StringSet.subset vlistfromformula vlistfromctrace then 
      let eval_val = Traceast.evaluate_formula_in_trace f ttrace in 
      match eval_val with 
      | Some(true) -> Printf.printf "SATISFIED\n" 
      | Some(false) -> Printf.printf "FALSIFIED\n" 
      | _ -> Printf.printf "ERROR: CAN BE CONSIDERED FALSE\n"
       
       
    else Printf.printf "ERROR: MISSING VARs in TRACE\n"
  else Printf.printf "ERROR: Inconsistent Trace\n"

let dump_formula _ =
  let input = read_line () in
  let f = Parserinterface.parse_formula input in
  let result = Ast.formulaToString f in 
  let () = Printf.printf "OK\n" in 
  print_endline result;
  Printf.printf "\n\n";
  print_endline ""
  let dump_signature _ =
    let input = read_line () in
    let f = Parserinterface.parse_formula input in
    let result = Ast.formulaToSignatureFormat f in 
    let () = Printf.eprintf "OK\n" in 
    print_endline result;
    Printf.printf "\n"
    (* print_endline "" *)

let dump_python _ =
    let input = read_line () in
    let f = Parserinterface.parse_formula input in
    let result = Ast.formulaToPython f in 
    (* let () = Printf.eprintf "OK\n" in  *)
    print_endline result
    (* Printf.printf "Iam here.....\n"; *)
    (* print_endline "" *)
    (* Printf.printf "\n" *)
    (* print_endline "" *)
    

let generate_random_formula _ = 
  (Utilfuncs.gen_ltl_formula() )  


let main_function _ =
  (* Printf.printf
    "The format of the input is that: a command should be followed by zero, \
     one, or two formulas (depending on the type of the command being executed)\n\
    \ \n\n\n\
     **** The command and each of its argument formula(s) should appear in a \
     line of its own****\n\n\n\n\
     Available commands:\n\
     [CHECKS EQUIVALENCE of TWO LTL FORMULAS] equiv formula_1 formula_2\n\
     [CHECKS WHETHER THE INPUT FORMULA CONTAINS PAST TEMPORAL OPERATORS or \
     PROPOSITIONAL LOGIC OPERATORS ONLY] check_past formula\n\
     [CHECKS WHETHER THE INPUT FORMULA ONLY CONTAINS FUTURE TEMPORAL OPERATORS \
     OR PROPOSITIONAL LOGIC OPERATORS ONLY] check_future formula\n\
     [GENERATES A TRACE THAT SATISFIES THE GIVEN FORMULA] positive_trace_gen \
     formula\n\
     [GENERATES A TRACE THAT FALSIFIES THE GIVEN FORMULA] negative_trace_gen \
     formula\n\
     [PRINTS THE GIVEN FORMULA] print_formula formula\n\n\n"; *)
  if Sys.file_exists nusmv_exe then
    (* let () = Printf.eprintf "NuSMV exe found in \"%s\"\n" nusmv_exe in   *)
    let raw_line = read_line () in
    let cmd = String.lowercase_ascii (String.trim raw_line) in
    if String.equal cmd "equiv" then check_equiv ()
    else if String.equal cmd "check_entailment" then check_entailment() 
    else if String.equal cmd "generate_random_formula" then generate_random_formula() 
    else if String.equal cmd "check_past" then check_past ()
    else if String.equal cmd "check_future" then check_future ()
    else if String.equal cmd "check_trace_satisfaction" then check_trace_satisfaction() 
    else if String.equal cmd "positive_trace_gen" then positive_trace_gen ()
    else if String.equal cmd "negative_trace_gen" then negative_trace_gen ()
    else if String.equal cmd "print_formula" then dump_formula () (* ()   *)
    else if String.equal cmd "print_signature" then dump_signature()
    else if String.equal cmd "print_python" then dump_python()   
    else if String.equal cmd "exit" then ()
    else Printf.eprintf "UNKNOWN COMMAND %s" cmd
  else
    failwith
      (String.cat "Fatal ERROR!!!\n Couldn't find NuSMV binary at: "
         nusmv_executable_full_path)

let _ = main_function ()
