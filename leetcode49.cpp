#include<iostream>
#include<string>
using namespace std;
int main() {
    string str[] = {"as","ghj","ghjgyi"};
    for(string s : str) {
        for(char c : s) {
            cout << int(c) << " ";
        }
        cout << endl;
    }
    return 0;
}