#include <iostream>
using namespace std;
class company{
    public:
        int income;
        company(int Income) : income(Income) {}
        virtual double calcTax() const{ return 0.0; }
        ~company() {}
};
class Service : public company{
    public:
        Service(int Income): company(Income) {}
        double calcTax() const override{return income * 0.05; }
};
class Manufacture : public company{
    public:
        Manufacture(int Income): company(Income) {}
        double calcTax() const override{return income * 0.17;}
};
int main(){
    char type;
    int income;
    double totalTax = 0.0;

    // 循环读取输入，直到文件结束 (EOF)
    while (cin >> type >> income) {
        company* ptr = nullptr;

        if (type == 'S') {
            ptr = new Service(income);
        } else if (type == 'M') {
            ptr = new Manufacture(income);
        }

        if (ptr != nullptr) {
            // 核心：通过父类指针调用虚函数，体现多态
            totalTax += ptr->calcTax();
            delete ptr; // 释放动态分配的内存
        }
    }

    // 输出结果，根据范例 390.25，建议保留必要的小数位
    cout << totalTax << endl;
    return 0;
}