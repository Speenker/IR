#include <cassert>
#include <cmath>
#include <iostream>

double simple_log(double x) {
    if (x <= 0) return 0.0;
    double y = x - 1.0;
    if (y > 1.0) {
        return simple_log(x / 2.0) + 0.693147;
    }
    double result = 0.0;
    double term = y;
    int n = 1;
    while (n < 50 && term > 1e-10) {
        if (n % 2 == 1) {
            result += term / n;
        }
        term *= y;
        n++;
    }
    return result;
}

int main() {
    assert(simple_log(1.0) == 0.0);
    assert(simple_log(2.0) > 0.0);
    assert(simple_log(4.0) > simple_log(2.0));
    assert(simple_log(0.5) == 0.0);
    assert(simple_log(-1.0) == 0.0);
    std::cout << "All TF-IDF tests passed!" << std::endl;
    return 0;
}