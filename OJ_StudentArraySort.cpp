#include <iostream>
#include<string>
using namespace std;
class student{
    public:
        string name;
        int math;
        int english;
        int total;
        string getName(){
            return name;
        }
        int getMath(){
            return math;
        }
        int getEnglish(){
            return english;
        }
        void calcTotal(){
            total = math+english;
        }
        int getTotal(){
            return total;
        }
        student() {
            name = "";
            math = 0;
            english = 0;
            total = 0;
        }
        student(string Name,int Math,int English){
            name = Name;
            math = Math;
            english = English;
        }
        student(const student &stu){
            name = stu.name;
            math = stu.math;
            english = stu.english;
            total = stu.total;
        }
};
void sortStudent(student stu[],int n){
    for(int i=0;i<n-1;i++){
        for(int j=0;j<n-i-1;j++){
            if(stu[j].total<stu[j+1].total){
                student temp = stu[j];
                stu[j] = stu[j+1];
                stu[j+1] = temp;
            }
        }
    }
}
int main(){
    student s[3],temp;
    string sName;
    int sMath, sEnglish;
    int i;
    for(i=0; i<3; i++){
        cin>>sName>>sMath>>sEnglish;
        s[i]=student(sName, sMath, sEnglish);
        s[i].calcTotal();
    }
    sortStudent(s, 3);
    for(i=0;i<3;i++){
        cout<<s[i].getName()<<" "<<s[i].getMath()<<" "<<s[i].getEnglish()<<" "<<s[i].getTotal()<<endl;
    }
    return 0;
}

