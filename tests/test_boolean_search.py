import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestQueryParsing:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.search_path = Path("src/search/search_cli.cpp").resolve()
        
        self.index_exe = self.test_dir / "index_builder.exe"
        self.search_exe = self.test_dir / "search_cli.exe"
        
        compile_result1 = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.index_exe), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        compile_result2 = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.search_exe), 
            str(self.search_path)
        ], capture_output=True, text=True)
        
        if compile_result1.returncode != 0 or compile_result2.returncode != 0:
            pytest.skip("Failed to compile binaries")
        
        self._build_test_index()
    
    def _build_test_index(self):
        manifest_path = self.test_dir / "test_manifest.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = [
            {
                "id": 1,
                "url": "http://example.com/doc1",
                "text": "python programming language tutorial",
                "title": "Python Tutorial"
            },
            {
                "id": 2,
                "url": "http://example.com/doc2",
                "text": "java programming development environment",
                "title": "Java Development"
            },
            {
                "id": 3,
                "url": "http://example.com/doc3",
                "text": "python programming machine learning artificial intelligence",
                "title": "AI with Python"
            },
            {
                "id": 4,
                "url": "http://example.com/doc4",
                "text": "web development html css javascript",
                "title": "Web Development"
            }
        ]
        
        manifest_lines = ['doc_id,final_url,text_path']
        
        for doc in test_docs:
            text_file = text_dir / f"doc{doc['id']}.txt"
            text_file.write_text(doc['text'], encoding='utf-8')
            manifest_lines.append(f'{doc["id"]},{doc["url"]},texts/doc{doc["id"]}.txt')
        
        manifest_path.write_text("\n".join(manifest_lines), encoding='utf-8')
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
    
    def test_simple_term_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        assert '1' in doc_ids
        assert '3' in doc_ids
    
    def test_boolean_and_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python && programming\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert '1' in doc_ids
        assert '3' in doc_ids
        assert '2' not in doc_ids
    
    def test_boolean_or_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python || java\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert '1' in doc_ids
        assert '2' in doc_ids
        assert '3' in doc_ids
    
    def test_boolean_not_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="programming !python\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert '2' in doc_ids
    
    def test_complex_boolean_query(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="(python || java) && programming\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert '1' in doc_ids
        assert '2' in doc_ids
        assert '3' in doc_ids
    
    def test_implicit_and_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python programming\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert '1' in doc_ids
        assert '3' in doc_ids
    
    def test_empty_result_search(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="nonexistentterm\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        assert len(output_lines) == 0 or output_lines == ['']
    
    def test_term_normalization(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="PYTHON\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        
        assert len(doc_ids) > 0
    
    def test_search_pagination(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin"),
            "--offset", "0",
            "--limit", "1"
        ], input="programming\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        doc_ids = [line.split('\t')[0] for line in output_lines if line.strip()]
        assert len(doc_ids) <= 1
    
    def test_error_handling(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "nonexistent.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="test\n", capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "ERROR" in result.stderr
    
    def test_query_parsing_edge_cases(self):
        test_queries = [
            "",
            "   ",
            "term1 term2 term3",
            "term1&&term2",
            "(term1 || term2) && term3",
            "!term1",
        ]
        
        for query in test_queries:
            result = subprocess.run([
                str(self.search_exe),
                "--inv", str(self.test_dir / "inv.bin"),
                "--fwd", str(self.test_dir / "fwd.bin")
            ], input=query + "\n", capture_output=True, text=True)
            
            assert result.returncode == 0 or result.returncode == 1


class TestIndexLoading:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.search_path = Path("src/search/search_cli.cpp").resolve()
        self.search_exe = self.test_dir / "search_cli.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.search_exe), 
            str(self.search_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip("Failed to compile search CLI")
    
    def test_missing_index_files(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "missing_inv.bin"),
            "--fwd", str(self.test_dir / "missing_fwd.bin")
        ], input="test\n", capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "ERROR" in result.stderr
    
    def test_invalid_magic_bytes(self):
        invalid_file = self.test_dir / "invalid.bin"
        invalid_file.write_bytes(b"INVALID")
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(invalid_file),
            "--fwd", str(self.test_dir / "missing_fwd.bin")
        ], input="test\n", capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "ERROR" in result.stderr


class TestResultFormat:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.search_path = Path("src/search/search_cli.cpp").resolve()
        
        self.index_exe = self.test_dir / "index_builder.exe"
        self.search_exe = self.test_dir / "search_cli.exe"
        
        compile_result1 = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.index_exe), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        compile_result2 = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.search_exe), 
            str(self.search_path)
        ], capture_output=True, text=True)
        
        if compile_result1.returncode != 0 or compile_result2.returncode != 0:
            pytest.skip("Failed to compile binaries")
        
        self._build_simple_index()
    
    def _build_simple_index(self):
        manifest_path = self.test_dir / "simple_manifest.csv"
        text_path = self.test_dir / "simple.txt"
        
        text_path.write_text("test document content", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'100,http://example.com/simple,simple.txt\n',
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
    
    def test_boolean_result_format(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="test && document\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if line.strip():
                parts = line.split('\t')
                assert len(parts) >= 3
                assert parts[0].isdigit()
    
    def test_single_term_result_format(self):
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="test\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4 and '.' in parts[1]:
                    try:
                        float(parts[1])
                    except ValueError:
                        assert False, "Score should be a number"