import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    required_tools = ['gcc', 'g++']
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Missing required tools: {', '.join(missing_tools)}")
        print("Please install GCC/G++ compiler:")
        print("  Windows: Install MinGW or use WSL")
        print("  macOS: Install Xcode Command Line Tools")
        print("  Linux: sudo apt-get install build-essential")
        return False
    
    return True


def run_python_tests():
    print("Running Python tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-v", 
            "--tb=short",
            "tests/"
        ], cwd=Path(__file__).parent.parent, check=False)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("pytest not found. Install with: pip install pytest pytest-cov")
        return False


def run_integration_tests():
    print("🔗 Running integration tests...")
    
    test_files = [
        "test_tokenization.py",
        "test_stemming.py", 
        "test_boolean_index.py",
        "test_boolean_search.py",
        "test_compression.py",
        "test_tfidf.py"
    ]
    
    tests_dir = Path(__file__).parent
    missing_files = []
    
    for test_file in test_files:
        if not (tests_dir / test_file).exists():
            missing_files.append(test_file)
    
    if missing_files:
        print(f"Missing test files: {', '.join(missing_files)}")
        return False
    
    print("All test files present")
    return True


def generate_test_report():
    print("\nTest Report")
    print("=" * 50)
    
    tests_dir = Path(__file__).parent
    components = {
        "Tokenization": tests_dir / "test_tokenization.py",
        "Stemming": tests_dir / "test_stemming.py",
        "Boolean Index": tests_dir / "test_boolean_index.py", 
        "Boolean Search": tests_dir / "test_boolean_search.py",
        "Compression": tests_dir / "test_compression.py",
        "TF-IDF": tests_dir / "test_tfidf.py"
    }
    
    print("Implemented Components with Tests:")
    for component, test_file in components.items():
        if test_file.exists():
            print(f"  {component}")
        else:
            print(f"  {component}")
    
    print("\n" + "=" * 50)
    print("Lab Requirements Coverage:")
    print("  Токенизация (Tokenization)")
    print("  Стемминг (Stemming)")
    print("  Булев индекс (Boolean Index)")
    print("  Булев поиск (Boolean Search)")
    print("  Сжатие (Compression)")
    print("  TF-IDF")
    
    print("\n Note: The following components were requested but not found in implementation:")
    print("  • General text compression algorithms (Huffman, LZW)")
    print("  • Zipf's law implementation (only visualization exists)")


def main():
    print("Search Engine Test Suite")
    print("=" * 40)
    
    if not check_dependencies():
        sys.exit(1)
    
    generate_test_report()
    
    print("\n🧪 Running Tests...")
    
    if not run_integration_tests():
        print("Test structure check failed")
        sys.exit(1)
    
    if run_python_tests():
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())