# LTL



### Dependencies 

- Install `opam`. Follow instructions in the following website: [https://opam.ocaml.org/doc/Install.html]

- `opam init`

- `opam install dune`

- `opam install merlin`

- `opam user-setup install`

- `opam install menhir`

- `opam install ocaml-lsp-server`

- Install the NuSMV model checker from the following website: [https://nusmv.fbk.eu/downloads.html]

 

### Execution 

- __NuSMV path:__ For compilation, there is a BASH script called `compile-project` where you should put your path of the `bin` folder of NuSMV. Please replace that full path with your computer's path to NuSMV. 

- Make the `compile-project` inside `LTL/corrected_version/ltlutils/` executable by running the following command in the terminal: `chmod a+x compile-project`

- Inside the `LTL/corrected_version/ltlutils/` directory run the following command in a Terminal: `./compile-project` 

-  Inside the `LTL/corrected_version/ltlutils/` directory run the following command in a Terminal : `dune build` `dune exec ./bin/main.exe < inp_file` 

### Input commands 

The program takes a command (e.g., `equiv`) and 0, 1, or 2 LTL formulas. 

__The command, and the formulas should appear in a separate line of its own. The current version cannot handle empty lines between the different arguments.__ (See the `inp_file` for a sample of the commands)

The program currently supports handling one command only. 

The program concretely supports the following commands: 

- `equiv f_1 f_2` (This command checks whether the two input formulas $f_1$ and $f_2$ are logically equivalent or not) 

- `check_past f` (This command checks to see whether the input formula $f$ contains only propositional logical operators and past temporal operators only; no future temporal operators.) 

- `check_future f` (This command checks to see whether the input formula $f$ contains only propositional logical operators and future temporal operators only; no past temporal operators.) 

- `positive_trace_gen f` (This command tries to generate a trace in the NuSMV trace format that __satisfies__ the given formula $f$. The trace is stored in the following file nusmv_executable_full_path/`trace.out`). Recall that, `nusmv_executable_full_path` refers to the location of NuSMV's `bin` folder in your system that you added in the `main.ml` file discussed above. 

- `negative_trace_gen f` (This command tries to generate a trace in the NuSMV trace format that __falsifies__ the given formula $f$. The trace is stored in the following file `nusmv_executable_full_path/trace.out`). Recall that, `nusmv_executable_full_path` refers to the location of NuSMV's `bin` folder in your system that you added in the `main.ml` file, as discussed above. 

- `print_formula f` (This command prints the input LTL formula $f$ in the NuSMV format.)

### Sample inputs 

The file `inp_file` contains examples of some commands and with its necessary arguments. Please note that only the first command will be executed and the rest of the commands will be ignored. You can write your own command file. 

Suppose you want to create a new command file called `testingLTL` and included the command along with its arguments. You execute that command file you should change how you execute the tool in the following way: `dune exec ./bin/main.exe < testingLTL`
