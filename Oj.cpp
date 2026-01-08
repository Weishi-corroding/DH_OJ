#include <iostream>
#include <string>
using namespace std;

int main() {
    int n;
    cin >> n;
    cin.ignore();
    for (int i = 0; i < n; i++) {
        string s;
        getline(cin, s);
        int count = 0;
        for (char c : s) {
            if (c >= '0' && c <= '9') {
                count++;
            }
        }
        cout << count << endl;
    }
    return 0;
}