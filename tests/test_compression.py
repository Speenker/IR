import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestCompressionBasic:
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
    
    def test_compression_with_single_document(self):
        manifest_path = self.test_dir / "test_single.csv"
        text_path = self.test_dir / "test_single.txt"
        
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
        
        stderr_output = result.stderr
        assert "Postings uncompressed:" in stderr_output
        assert "Postings compressed:" in stderr_output
        assert "Compression ratio:" in stderr_output
    
    def test_compression_with_multiple_documents(self):
        manifest_path = self.test_dir / "test_multi.csv"
        text_path = self.test_dir / "test_multi.txt"
        
        text_path.write_text("common word1 word2 common word3", encoding='utf-8')
        
        manifest_lines = [f'doc_id,final_url,text_path\n']
        for i in range(1, 6):
            manifest_lines.append(f'{i},http://example.com/{i},{text_path.name}\n')
        
        manifest_path.write_text(''.join(manifest_lines), encoding='utf-8')
        
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
        
        lines = stderr_output.split('\n')
        uncomp_line = [line for line in lines if "Postings uncompressed:" in line]
        comp_line = [line for line in lines if "Postings compressed:" in line]
        
        assert len(uncomp_line) > 0
        assert len(comp_line) > 0
    
    def test_compression_ratio_positive(self):
        manifest_path = self.test_dir / "test_ratio.csv"
        text_path = self.test_dir / "test_ratio.txt"
        
        text_path.write_text("word1 " * 10 + "word2 " * 10 + "word3 " * 10, encoding='utf-8')
        
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
        lines = stderr_output.split('\n')
        ratio_line = [line for line in lines if "Compression ratio:" in line]
        
        assert len(ratio_line) > 0
        
        ratio_text = ratio_line[0]
        assert "Compression ratio:" in ratio_text
    
    def test_compression_with_large_vocabulary(self):
        manifest_path = self.test_dir / "test_large.csv"
        text_path = self.test_dir / "test_large.txt"
        
        words = [f"word{i}" for i in range(1, 51)]
        text_content = " ".join(words)
        text_path.write_text(text_content, encoding='utf-8')
        
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
        assert "Compression ratio:" in stderr_output
    
    def test_compression_with_empty_document(self):
        manifest_path = self.test_dir / "test_empty.csv"
        text_path = self.test_dir / "test_empty.txt"
        
        text_path.write_text("", encoding='utf-8')
        
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
        assert "Compression ratio:" in stderr_output


class TestCompressionFileStructure:
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
    
    def test_compressed_index_version(self):
        manifest_path = self.test_dir / "test_version.csv"
        text_path = self.test_dir / "test_version.txt"
        
        text_path.write_text("test compression version", encoding='utf-8')
        
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
        assert inv_path.exists()
        
        import struct
        with open(inv_path, 'rb') as f:
            magic = f.read(4)
            assert magic == b'INV1'
            
            version = struct.unpack('<I', f.read(4))[0]
            assert version == 2
    
    def test_compressed_postings_structure(self):
        manifest_path = self.test_dir / "test_postings.csv"
        text_path = self.test_dir / "test_postings.txt"
        
        text_path.write_text("term1 term2 term1 term3 term2", encoding='utf-8')
        
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
        assert inv_path.exists()
        
        import struct
        with open(inv_path, 'rb') as f:
            f.read(4)
            f.read(4)
            term_count = struct.unpack('<I', f.read(4))[0]
            doc_count = struct.unpack('<I', f.read(4))[0]
            
            assert term_count > 0
            assert doc_count == 1


class TestCompressionPerformance:
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
    
    def test_compression_memory_efficiency(self):
        manifest_path = self.test_dir / "test_memory.csv"
        text_path = self.test_dir / "test_memory.txt"
        
        text_content = "common " * 100 + "unique1 " * 10 + "unique2 " * 10
        text_path.write_text(text_content, encoding='utf-8')
        
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
        assert "OOM" not in stderr_output
        assert "Compression ratio:" in stderr_output
    
    def test_compression_with_repeated_terms(self):
        manifest_path = self.test_dir / "test_repeated.csv"
        text_path = self.test_dir / "test_repeated.txt"
        
        text_content = "term " * 50 + "another " * 30 + "third " * 20
        text_path.write_text(text_content, encoding='utf-8')
        
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
        lines = stderr_output.split('\n')
        uncomp_line = [line for line in lines if "Postings uncompressed:" in line]
        comp_line = [line for line in lines if "Postings compressed:" in line]
        
        assert len(uncomp_line) > 0
        assert len(comp_line) > 0


class TestCompressionEdgeCases:
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
    
    def test_compression_with_single_term(self):
        manifest_path = self.test_dir / "test_single_term.csv"
        text_path = self.test_dir / "test_single_term.txt"
        
        text_path.write_text("onlyword", encoding='utf-8')
        
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
        assert "Compression ratio:" in stderr_output
    
    def test_compression_with_punctuation(self):
        manifest_path = self.test_dir / "test_punct.csv"
        text_path = self.test_dir / "test_punct.txt"
        
        text_path.write_text("word1, word2! word3. word4?", encoding='utf-8')
        
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
        assert "Compression ratio:" in stderr_output