import pytest
import subprocess
import tempfile
import os
from pathlib import Path
import struct


class TestIndexBuilderBasic:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_manifest_parsing(self):
        manifest_path = self.test_dir / "test_manifest.csv"
        text_path = self.test_dir / "test_doc.txt"
        
        text_path.write_text("test content", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        inv_path = self.test_dir / "inv.bin"
        fwd_path = self.test_dir / "fwd.bin"
        
        assert inv_path.exists()
        assert fwd_path.exists()
    
    def test_manifest_with_missing_columns(self):
        manifest_path = self.test_dir / "test_bad_manifest.csv"
        text_path = self.test_dir / "test_doc.txt"
        
        text_path.write_text("test content", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,text_path\n'
            f'1,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "ERROR" in result.stderr
    
    def test_file_not_found(self):
        manifest_path = self.test_dir / "test_missing.csv"
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,nonexistent.txt\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        inv_path = self.test_dir / "inv.bin"
        fwd_path = self.test_dir / "fwd.bin"
        
        assert inv_path.exists()
        assert fwd_path.exists()
        
        stderr_output = result.stderr
        assert "Docs: 0" in stderr_output
        assert "Unique terms: 0" in stderr_output
        assert "Tokens total: 0" in stderr_output


class TestIndexOptions:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_yo2e_option(self):
        manifest_path = self.test_dir / "test_yo2e.csv"
        text_path = self.test_dir / "test_yo2e.txt"
        
        text_path.write_text("ёлка ёжик", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--yo2e", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        result2 = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--yo2e", "0"
        ], capture_output=True, text=True)
        
        assert result2.returncode == 0
    
    def test_keepnumbers_option(self):
        manifest_path = self.test_dir / "test_numbers.csv"
        text_path = self.test_dir / "test_numbers.txt"
        
        text_path.write_text("test 123 word 456", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--keepnumbers", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        result2 = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--keepnumbers", "0"
        ], capture_output=True, text=True)
        
        assert result2.returncode == 0
    
    def test_minlen_option(self):
        manifest_path = self.test_dir / "test_minlen.csv"
        text_path = self.test_dir / "test_minlen.txt"
        
        text_path.write_text("a ab abc abcde", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--minlen", "3"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
    
    def test_maxdocbytes_option(self):
        manifest_path = self.test_dir / "test_maxbytes.csv"
        text_path = self.test_dir / "test_maxbytes.txt"
        
        text_path.write_text("word " * 1000, encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir),
            "--maxdocbytes", "100"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0


class TestIndexFileStructure:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_inv_bin_header(self):
        manifest_path = self.test_dir / "test_header.csv"
        text_path = self.test_dir / "test_header.txt"
        
        text_path.write_text("word1 word2 word3", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        inv_path = self.test_dir / "inv.bin"
        with open(inv_path, 'rb') as f:
            magic = f.read(4)
            assert magic == b'INV1'
            
            version = struct.unpack('<I', f.read(4))[0]
            assert version == 2
            
            term_count = struct.unpack('<I', f.read(4))[0]
            doc_count = struct.unpack('<I', f.read(4))[0]
            
            assert term_count > 0
            assert doc_count == 1
    
    def test_fwd_bin_header(self):
        manifest_path = self.test_dir / "test_fwd.csv"
        text_path = self.test_dir / "test_fwd.txt"
        
        text_path.write_text("test document", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'42,http://example.com/test,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        fwd_path = self.test_dir / "fwd.bin"
        with open(fwd_path, 'rb') as f:
            magic = f.read(4)
            assert magic == b'FWD1'
            
            version = struct.unpack('<I', f.read(4))[0]
            assert version == 1
            
            doc_count = struct.unpack('<I', f.read(4))[0]
            assert doc_count == 1
            
            min_docid = struct.unpack('<I', f.read(4))[0]
            max_docid = struct.unpack('<I', f.read(4))[0]
            assert min_docid == 42
            assert max_docid == 42


class TestMultipleDocuments:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_multiple_docs_same_terms(self):
        manifest_path = self.test_dir / "test_multi.csv"
        text_path = self.test_dir / "test_multi.txt"
        
        text_path.write_text("common word", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com/1,{text_path.name}\n'
            f'2,http://example.com/2,{text_path.name}\n'
            f'3,http://example.com/3,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        inv_path = self.test_dir / "inv.bin"
        with open(inv_path, 'rb') as f:
            f.read(4)
            f.read(4)
            term_count = struct.unpack('<I', f.read(4))[0]
            doc_count = struct.unpack('<I', f.read(4))[0]
            
            assert doc_count == 3
    
    def test_sequential_doc_ids(self):
        manifest_path = self.test_dir / "test_seq.csv"
        text_path = self.test_dir / "test_seq.txt"
        
        text_path.write_text("test content", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'10,http://example.com/10,{text_path.name}\n'
            f'20,http://example.com/20,{text_path.name}\n'
            f'30,http://example.com/30,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        fwd_path = self.test_dir / "fwd.bin"
        with open(fwd_path, 'rb') as f:
            f.read(4)
            f.read(4)
            f.read(4)
            min_docid = struct.unpack('<I', f.read(4))[0]
            max_docid = struct.unpack('<I', f.read(4))[0]
            
            assert min_docid == 10
            assert max_docid == 30


class TestCompressionVerification:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_compression_stats_present(self):
        manifest_path = self.test_dir / "test_compress.csv"
        text_path = self.test_dir / "test_compress.txt"
        
        text_path.write_text("word1 word2 word1 word2 word3", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "Postings uncompressed:" in stderr_output
        assert "Postings compressed:" in stderr_output
        assert "Compression ratio:" in stderr_output


class TestStatistics:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.index_path = Path("src/index/build_index.cpp").resolve()
        self.executable_path = self.test_dir / "index_builder_test.exe"
        
        compile_result = subprocess.run([
            "g++", "-O2", "-std=c++17", "-o", str(self.executable_path), 
            str(self.index_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile: {compile_result.stderr}")
    
    def test_output_statistics(self):
        manifest_path = self.test_dir / "test_stats.csv"
        text_path = self.test_dir / "test_stats.txt"
        
        text_path.write_text("hello world hello python programming world", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,final_url,text_path\n'
            f'1,http://example.com,{text_path.name}\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "Docs: 1" in stderr_output
        assert "Unique terms:" in stderr_output
        assert "Tokens total:" in stderr_output
        assert "Avg token length" in stderr_output
        assert "Avg term length" in stderr_output
        assert "Indexing time" in stderr_output
        assert "Time per doc" in stderr_output
        assert "Wrote:" in stderr_output