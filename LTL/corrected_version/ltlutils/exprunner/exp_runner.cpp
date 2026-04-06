# include <cstdio> 
# include <cstring>
# include <cstdlib> 
# include <string>
# include <iostream> 
# include <vector> 
# include <set> 
# include <map> 
# include <cerrno>
# include <cassert> 
# include <sstream>

using namespace std ; 

FILE *fin; 

int num_col ;
int total_data_rows ; 

vector <string> column_names ; 
vector <string> orig_column_names ; 

bool hasNewLine(std::string S){
    for(int i = 0 ; i < S.length(); ++i){
        if(S[i]=='\n') return true ; 
    }return false ; 
}


vector< vector<string> > data ; 
vector<vector<string> > orig_data ; 

// vector< vector<string> > equiv_result_data ; 
// vector< vector<string> > entailment_result_data ; 
int equiv_total = 0 ; 
int entailment_total = 0 ; 

void toggle(bool &flag)
{
    flag = !flag ; 
}

void fill_result_table_columns()
{
    for(int r = 0 ; r < total_data_rows ; ++r)
    {
        vector<string> VS ; 
        for(int i = 1 ; i < num_col ; ++i)
        {
            for(int j = i + 1 ; j < num_col ; ++j)
            {
                string f1 = data[r][i] ; 
                string f2 = data[r][j] ; 
                FILE * fw = fopen("inp", "w") ;
                if(!fw){
                    cerr << "EQUIV ERROR: Cannot open file inp for writing\n" ; 
                    assert(0); 
                } 
                fprintf(fw, "equiv\n%s\n%s\n",f1.c_str(), f2.c_str()) ; 
                fclose(fw) ; 
                int ret_code = system("dune exec ./bin/main.exe < inp 1> out.log 2>> ocaml_error.log") ; 
                bool error = false ; 
                if(ret_code)
                {
                    error = true ; 
                    cerr << "F1: " <<  f1 << " F2: " << f2 << endl ; 
                    cerr << "EQUIV ERROR: Equiv Command did not execute properly. Terminated with code: " << ret_code << endl ; 
                    // assert(0) ; 
                }
                if(!error)
                {
                     FILE *fr = fopen("out.log", "r") ; 
                    if(!fr)
                    {
                        cerr << "EQUIV ERROR: Cannot open file out for reading\n" ; 
                        assert(0) ; 
                    }
                    char buff[1024] ; 
                    assert(fscanf(fr, "%s", buff) == 1) ;
                    VS.push_back(std::string(buff)) ; 
                    fclose(fr) ;   
                }
                else VS.push_back("ERROR") ;  
                 
            }
        }
        assert(VS.size() == equiv_total) ; 
        data[r].insert(data[r].end(), VS.begin(), VS.end()) ; 
    }

    for(int r = 0 ; r < total_data_rows ; ++r)
    {
        vector<string> VS ; 
        for(int i = 1 ; i < num_col ; ++i)
        {
            for(int j = 1 ; j < num_col ; ++j)
            {
                if(i==j) continue ; 
                string f1 = data[r][i] ; 
                string f2 = data[r][j] ; 
                FILE * fw = fopen("inp", "w") ;
                if(!fw){
                    cerr << "ENTAILMENT ERROR: Cannot open file inp for writing\n" ; 
                    assert(0); 
                } 
                fprintf(fw, "check_entailment\n%s\n%s\n",f1.c_str(), f2.c_str()) ; 
                fclose(fw) ; 
                bool error = false ; 
                int ret_code = system("dune exec ./bin/main.exe < inp 1> out.log 2>> ocaml_error.log") ; 
                if(ret_code)
                {
                    error = true ; 
                    cerr << "F1: " <<  f1 << " F2: " << f2 << endl ; 
                    cerr << "ENTAILMENT ERROR: Equiv Command did not execute properly. Terminated with code: " << ret_code << endl ; 
                    // assert(0) ; 
                }
                if(!error){
                    FILE *fr = fopen("out.log", "r") ; 
                    if(!fr)
                    {
                        cerr << "ENTAILMENT ERROR: Cannot open file out for reading\n" ; 
                        assert(0) ; 
                    }
                    char buff[1024] ; 
                    assert(fscanf(fr, "%s", buff) == 1) ;
                    VS.push_back(std::string(buff)) ;
                    fclose(fr) ; 
                }
                else VS.push_back("ERROR");  
                 
            }
        }
        assert(VS.size() == entailment_total) ; 
        data[r].insert(data[r].end(), VS.begin(), VS.end()) ; 
    }

    for(int r = 0 ; r < total_data_rows ; ++r)
    {
        vector<string> VS ; 
        for(int i = 1 ; i < num_col ; ++i)
        {
            string formula = data[r][i] ; 
            FILE * fw = fopen("inp", "w") ;
                if(!fw){
                    cerr << "SYNTAX CHECK ERROR: Cannot open file inp for writing\n" ; 
                    assert(0); 
                } 
                fprintf(fw, "print_formula\n%s\n",formula.c_str()) ; 
                fclose(fw) ; 
                bool error = false ; 
                int ret_code = system("dune exec ./bin/main.exe < inp 1> out.log 2>> ocaml_error.log") ; 
                if(ret_code)
                {
                    error = true ; 
                    cerr << "F: " <<  formula << endl ; 
                    cerr << "SYNTAX CHECK ERROR: SYNTAX Command did not execute properly. Terminated with code: " << ret_code << endl ; 
                    // assert(0) ; 
                }
                if(!error){
                    FILE *fr = fopen("out.log", "r") ; 
                    if(!fr)
                    {
                        cerr << "SYNTAX CHECK ERROR: Cannot open file out for reading\n" ; 
                        assert(0) ; 
                    }
                    char buff[1024] ; 
                    assert(fscanf(fr, "%s", buff) == 1) ;
                    VS.push_back(std::string(buff)) ;
                    fclose(fr) ; 
                }
                else VS.push_back("ERROR");  
        }
        assert(VS.size() == num_col-1) ; 
        data[r].insert(data[r].end(), VS.begin(), VS.end()) ; 

    }

}

void fill_result_table_column_names()
{
    vector <string> X; 
    X.clear() ; 
    // vector <string> entailment_column_names; 
    for(int i = 1 ; i < num_col ; ++i)
    {
        for(int j = i + 1 ; j < num_col ; ++j)
        {
            // char buff[1024] ; 
            // sprintf(buff, "%s <-> %s", column_names[i].c_str(), column_names[j].c_str()) ; 
            std::ostringstream tout;
            tout <<  "Eq+" <<column_names[i] << "+" << column_names[j] ;
            string sname = tout.str(); 
            sname.erase(std::remove(sname.begin(), sname.end(), '\n'), sname.end());
            X.push_back(sname) ; 
            ++equiv_total ; 
        }
    }
    column_names.insert(column_names.end(), X.begin(), X.end());

    X.clear() ; 

    for(int i = 1 ; i < num_col ; ++i)
    {
        for(int j = 1 ; j < num_col ; ++j)
        {
            if(i==j) continue ; 
            // char buff[1024] ; 
            std::ostringstream sout;
            sout << "En+" << column_names[i] << "+" << column_names[j];
            string sname = sout.str(); 
            sname.erase(std::remove(sname.begin(), sname.end(), '\n'), sname.end());
            // sprintf(buff, "%s -> %s", column_names[i].c_str(), column_names[j].c_str()) ; 
            X.push_back(sname) ; 
            ++entailment_total ; 
        }
    }
    column_names.insert(column_names.end(), X.begin(), X.end()) ; 
    cerr << "EQUIV TOTAL: " << equiv_total << "\nEntailment TOTAL: " << entailment_total << endl ; 

    /*NEW CODE .....*/
    X.clear() ; 

    for(int i = 1 ; i < num_col ; ++i)
    {
            std::ostringstream sout;
            sout << "Syntax-check-" << column_names[i];
            string sname = sout.str(); 
            sname.erase(std::remove(sname.begin(), sname.end(), '\n'), sname.end());
            X.push_back(sname) ; 
    }
    column_names.insert(column_names.end(), X.begin(), X.end()) ; 
    /*NEW CODE .....*/

}

std::pair<int, string> get_ground_truth(char * line)
{
    bool found_quote = false ;
    int counter = 0 ; 
    int len = strlen(line) ; 
    for( ; counter < len; ++counter)
    {
        if(line[counter] == '\"'){
            toggle(found_quote) ; 
            continue ; 
        }
        if(line[counter] ==',')
        {
            if(found_quote) continue ; 
            else{
                line[counter] ='\0' ; 
                break ; 
            }
        }
    }
    if(counter >= len-1) assert(0) ; 
    return std::make_pair(counter +1, std::string(line) ) ; 
}



void tokenize_rest_of_the_columns(char *line, vector<string> &vals, int& ncol)
{
    char *ptr = strtok(line, ",\n\r") ; 
    while(ptr){
        ++ncol ; 
        std::string temp_cp = ptr ; 
        vals.push_back(temp_cp) ; 
        ptr = strtok(NULL, ",\n\r") ; 
    }
}

char line[5000000];
void process_csv() 
{
    column_names.clear() ; 
    // char line[10000000]; 
    if(fgets(line, sizeof(line), fin))
    {
        cerr << "First line read from input file is as follows:" << endl ;
        cerr << line << endl ;
        std::pair< int, std::string> r = get_ground_truth(line) ; 
        if(r.second == ""){
            cerr << "Could you read the value of the first column of the first row" << endl ; 
            assert(0) ;
        } 
        column_names.push_back(r.second) ; 
        num_col = 1 ; 
        tokenize_rest_of_the_columns(line+r.first, column_names, num_col) ; 

    }
    else{
        cerr << "Could not read first line from input file" << endl ; 
        assert(0) ; 
    }
    orig_column_names = column_names ; //new code storing original column names ... 
    for(int x = 0 ; x < orig_column_names.size() ; ++x){
        cerr << orig_column_names[x] << endl ;
    }
    int row_num = 1 ; 
    data.clear() ; 
    while(fgets(line, sizeof (line), fin))
    {
        if(row_num == 47){
            cerr << "Row " << row_num << " data is as follows:" <<endl ; 
            cerr << line << endl ;
        }
        vector<string> row ;
        row.clear() ; 
        int col_in_cur_row = 0 ;  
        std::pair< int, std::string> r = get_ground_truth(line) ; 
        if(r.second == ""){
            cerr << "Could you read the value of the first column of row " << row_num << endl ; 
            assert(0) ;
        }
        col_in_cur_row = 1 ; 
        row.push_back(r.second) ; //ground_truth_pushed 
        tokenize_rest_of_the_columns(line+r.first, row, col_in_cur_row) ; 
        if(num_col != col_in_cur_row)
        {
            cerr << "Number of columns in the initial row is " << num_col << endl ;
            cerr << "Number of columns in row " << row_num << " is " << col_in_cur_row << endl ;
            cerr << "Number of columns in row " << row_num << " is not equal to number of columns in the first row" << endl ; 
            assert(0) ; 
        }
        // assert(num_col == col_in_cur_row) ; 
        data.push_back(row) ; 
        ++row_num ; 
    }
    total_data_rows = row_num - 1 ; 
    cerr << "TOTAL DATA ROWS READ: " << total_data_rows << endl ; 
    orig_data = data ; // new code storing original data rows ... 

}

void dump_parsed_csv_file()
{
    for(int i = 0 ; i < column_names.size() ; ++i){
        if(hasNewLine(column_names[i])) assert(0) ; 
        if(i) cout << "," ; 
        cout << column_names[i] ; 
    }
    cout << endl ; 
    for(int i = 0 ; i < data.size() ; ++i)
    {
        for(int j = 0 ; j < data[i].size() ; ++j)
        {
            if(j) cout << "," ; 
            cout << data[i][j] ; 
        }
        cout << endl ; 
    }
    
}

int main(int argc, char *argv[])
{
    if(argc != 2)
    {
        cerr << "Usage: ./exp_runner name_of_the_input.csv\n" ; 
        return 1 ; 
    }
    fin = fopen(argv[1], "r") ; 
    if(!fin){
        cerr << "Could not open input CSV file: " << argv[1] << endl ; 
        return 1 ; 
    }
    // fout = fopen(argv[2], "w") ;
    // if(!fout){
    //     cerr << "Could not open output CSV file: " << argv[2] << endl ; 
    // }
    process_csv(); 
    fill_result_table_column_names(); 
    fill_result_table_columns() ; 
    dump_parsed_csv_file(); 
    fclose(fin) ; 
    // fclose(fout) ; 
    return 0 ; 
}