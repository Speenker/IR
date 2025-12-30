#include <iostream>
#include <cstdlib>

int main() {
    std::cout << "Running test_boolean_index..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_boolean_index.exe test_boolean_index.cpp && test_boolean_index.exe") != 0) {
        std::cout << "test_boolean_index failed!" << std::endl;
        return 1;
    }

    std::cout << "Running test_boolean_search..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_boolean_search.exe test_boolean_search.cpp && test_boolean_search.exe") != 0) {
        std::cout << "test_boolean_search failed!" << std::endl;
        return 1;
    }

    std::cout << "Running test_compression..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_compression.exe test_compression.cpp && test_compression.exe") != 0) {
        std::cout << "test_compression failed!" << std::endl;
        return 1;
    }

    std::cout << "Running test_stemming..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_stemming.exe test_stemming.cpp && test_stemming.exe") != 0) {
        std::cout << "test_stemming failed!" << std::endl;
        return 1;
    }

    std::cout << "Running test_tfidf..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_tfidf.exe test_tfidf.cpp && test_tfidf.exe") != 0) {
        std::cout << "test_tfidf failed!" << std::endl;
        return 1;
    }

    std::cout << "Running test_tokenization..." << std::endl;
    if (std::system("g++ -O2 -std=c++17 -o test_tokenization.exe test_tokenization.cpp && test_tokenization.exe") != 0) {
        std::cout << "test_tokenization failed!" << std::endl;
        return 1;
    }

    std::cout << "All tests passed!" << std::endl;
    return 0;
}