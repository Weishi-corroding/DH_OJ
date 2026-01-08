#include<iostream>
#include<cstring>
using namespace std;
class Student{
    private:
        char name[15];
        int norm,ex,final,overall;
    public:
        Student(){}
        void init(char *name1, int nor1, int ex1, int fin1){
            strcpy(name, name1);
            norm = nor1;
            ex = ex1;
            final = fin1;
            overall = nor1 + ex1 + fin1;
        }
        void fun(){
            overall = norm*20/100 + ex*25/100 + final*55/100;
        }
        void print(){
            cout<<name<<" "<<overall<<endl;
        }
        friend void sort(Student st[], int n){
            for(int i=0;i<n-1;i++){
                for(int j=0;j<n-i-1;j++){
                    if(st[j].overall<st[j+1].overall){
                        Student temp = st[j];
                        st[j] = st[j+1];
                        st[j+1] = temp;
                    }
                }
            }
        }
};
int main() {
   int n, i;
   int norm, ex, final;
   char name[15];
   cin >> n;
   Student stu[1000];
   for (i = 0; i < n; i++) {
       cin >> name >> norm >> ex >> final;
       stu[i].init(name, norm, ex, final);
       stu[i].fun();
   }
   sort(stu, n);
   for (i = 0; i < n; i++) {
       stu[i].print();
   }
   return 0;
}