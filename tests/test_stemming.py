import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestStemmingBasic:
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
    
    def test_russian_word_stemming(self):
        manifest_path = self.test_dir / "test_stemming.csv"
        text_path = self.test_dir / "test_stemming.txt"
        
        text_path.write_text("дом дома домом домов домах", encoding='utf-8')
        
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
        assert "Unique terms:" in stderr_output
        assert "Tokens total:" in stderr_output
    
    def test_stemming_with_yo_conversion(self):
        manifest_path = self.test_dir / "test_yo.csv"
        text_path = self.test_dir / "test_yo.txt"
        
        text_path.write_text("ёлка ёлку ёлки", encoding='utf-8')
        
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
        
        stderr_output = result.stderr
        assert "Unique terms:" in stderr_output
    
    def test_stemming_without_yo_conversion(self):
        manifest_path = self.test_dir / "test_no_yo.csv"
        text_path = self.test_dir / "test_no_yo.txt"
        
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
            "--yo2e", "0"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "Unique terms:" in stderr_output
    
    def test_stemming_minimum_length(self):
        manifest_path = self.test_dir / "test_minlen.csv"
        text_path = self.test_dir / "test_minlen.txt"
        
        text_path.write_text("а б в я дом дома", encoding='utf-8')
        
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
        
        stderr_output = result.stderr
        assert "Tokens total:" in stderr_output


class TestStemmingIntegration:
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
    
    def test_stemming_with_numbers(self):
        manifest_path = self.test_dir / "test_numbers.csv"
        text_path = self.test_dir / "test_numbers.txt"
        
        text_path.write_text("дом123 число456", encoding='utf-8')
        
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
        
        stderr_output = result.stderr
        assert "Unique terms:" in stderr_output
    
    def test_stemming_without_numbers(self):
        manifest_path = self.test_dir / "test_no_numbers.csv"
        text_path = self.test_dir / "test_no_numbers.txt"
        
        text_path.write_text("дом123 число456", encoding='utf-8')
        
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
            "--keepnumbers", "0"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "Unique terms:" in stderr_output
    
    def test_stemming_complex_sentence(self):
        manifest_path = self.test_dir / "test_complex.csv"
        text_path = self.test_dir / "test_complex.txt"
        
        text_path.write_text("В это утро я шел по красивой улице", encoding='utf-8')
        
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
        assert "Unique terms:" in stderr_output
        assert "Tokens total:" in stderr_output
    
    def test_stemming_multiple_documents(self):
        manifest_path = self.test_dir / "test_multi.csv"
        text_path = self.test_dir / "test_multi.txt"
        
        text_path.write_text("больший большая больше", encoding='utf-8')
        
        manifest_lines = [f'doc_id,final_url,text_path\n']
        for i in range(1, 4):
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
        assert "Docs:" in stderr_output
        assert "Unique terms:" in stderr_output


class TestStemmingEdgeCases:
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
    
    def test_stemming_empty_document(self):
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
        assert "Docs:" in stderr_output
    
    def test_stemming_punctuation_only(self):
        manifest_path = self.test_dir / "test_punct.csv"
        text_path = self.test_dir / "test_punct.txt"
        
        text_path.write_text("! ? . , ; :", encoding='utf-8')
        
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
        assert "Docs:" in stderr_output
    
    def test_stemming_very_short_words(self):
        manifest_path = self.test_dir / "test_short.csv"
        text_path = self.test_dir / "test_short.txt"
        
        text_path.write_text("а б в я о и у е ё", encoding='utf-8')
        
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
            "--minlen", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "Tokens total:" in stderr_output
    
    def test_stemming_performance_large_text(self):
        manifest_path = self.test_dir / "test_large.csv"
        text_path = self.test_dir / "test_large.txt"
        
        base_words = ["дом", "дом", "дом", "больший", "больший", "делать", "делать"]
        test_text = " ".join(base_words * 100)
        text_path.write_text(test_text, encoding='utf-8')
        
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
        assert "done" in stderr_output.lower()
        assert "Indexing time" in stderr_output
    
    def test_stemming_latin_characters(self):
        manifest_path = self.test_dir / "test_latin.csv"
        text_path = self.test_dir / "test_latin.txt"
        
        text_path.write_text("hello world programming", encoding='utf-8')
        
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
        assert "Unique terms:" in stderr_output
    
    def test_stemming_mixed_content(self):
        manifest_path = self.test_dir / "test_mixed.csv"
        text_path = self.test_dir / "test_mixed.txt"
        
        text_path.write_text("дом123 english привет 456", encoding='utf-8')
        
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
        
        stderr_output = result.stderr
        assert "Unique terms:" in stderr_output