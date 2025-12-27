import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestTokenizationBasic:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.tokenizer_path = Path("scripts/tokenizer.c").resolve()
        self.executable_path = self.test_dir / "tokenizer_test.exe"
        
        compile_result = subprocess.run([
            "gcc", "-O2", "-o", str(self.executable_path), 
            str(self.tokenizer_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile tokenizer: {compile_result.stderr}")
    
    def test_basic_tokenization(self):
        manifest_path = self.test_dir / "test_basic.csv"
        text_path = self.test_dir / "test_basic.txt"
        
        text_path.write_text("hello world test", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        assert term_freq_path.exists()
        
        terms = term_freq_path.read_text(encoding='utf-8')
        assert "hello" in terms.lower()
        assert "world" in terms.lower()
        assert "test" in terms.lower()
    
    def test_cyrillic_tokenization(self):
        manifest_path = self.test_dir / "test_cyrillic.csv"
        text_path = self.test_dir / "test_cyrillic.txt"
        
        text_path.write_text("привет мир тест", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "привет" in terms
        assert "мир" in terms
    
    def test_yo_to_e_conversion(self):
        manifest_path = self.test_dir / "test_yo.csv"
        text_path = self.test_dir / "test_yo.txt"
        
        text_path.write_text("ёлка ёжик", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir),
            "--yo-to-e", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "елка" in terms
        assert "ежик" in terms
    
    def test_minimum_length_filtering(self):
        manifest_path = self.test_dir / "test_minlen.csv"
        text_path = self.test_dir / "test_minlen.txt"
        
        text_path.write_text("a ab abc", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir),
            "--min-len", "3"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "a," not in terms
        assert "ab," not in terms
        assert '"abc",1' in terms
    
    def test_keep_numbers_option(self):
        manifest_path = self.test_dir / "test_numbers.csv"
        text_path = self.test_dir / "test_numbers.txt"
        
        text_path.write_text("test 123 word 456", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir),
            "--keep-numbers", "1"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms_with_numbers = term_freq_path.read_text(encoding='utf-8')
        assert "123" in terms_with_numbers
        
        result2 = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir),
            "--keep-numbers", "0"
        ], capture_output=True, text=True)
        
        assert result2.returncode == 0
        
        terms_without_numbers = term_freq_path.read_text(encoding='utf-8')
        assert "123" not in terms_without_numbers


class TestTokenizationUTF8:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.tokenizer_path = Path("scripts/tokenizer.c").resolve()
        self.executable_path = self.test_dir / "tokenizer_test.exe"
        
        compile_result = subprocess.run([
            "gcc", "-O2", "-o", str(self.executable_path), 
            str(self.tokenizer_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile tokenizer: {compile_result.stderr}")
    
    def test_mixed_languages(self):
        manifest_path = self.test_dir / "test_mixed.csv"
        text_path = self.test_dir / "test_mixed.txt"
        
        text_path.write_text("hello привет world мир", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "hello" in terms.lower()
        assert "привет" in terms
        assert "world" in terms.lower()
        assert "мир" in terms
    
    def test_special_characters(self):
        manifest_path = self.test_dir / "test_special.csv"
        text_path = self.test_dir / "test_special.txt"
        
        text_path.write_text("test-word test_word test.word", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "test-word" in terms
        assert '"test",2' in terms
        assert '"word",2' in terms
    
    def test_punctuation_handling(self):
        manifest_path = self.test_dir / "test_punct.csv"
        text_path = self.test_dir / "test_punct.txt"
        
        text_path.write_text("hello, world! test? doc.", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "hello" in terms.lower()
        assert "world" in terms.lower()
        assert "test" in terms.lower()
        assert "doc" in terms.lower()
    
    def test_case_normalization(self):
        manifest_path = self.test_dir / "test_case.csv"
        text_path = self.test_dir / "test_case.txt"
        
        text_path.write_text("HELLO World Test", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "hello" in terms.lower()
        assert "world" in terms.lower()
        assert "test" in terms.lower()


class TestTokenizationIntegration:
    def setup_method(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.tokenizer_path = Path("scripts/tokenizer.c").resolve()
        self.executable_path = self.test_dir / "tokenizer_test.exe"
        
        compile_result = subprocess.run([
            "gcc", "-O2", "-o", str(self.executable_path), 
            str(self.tokenizer_path)
        ], capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            pytest.skip(f"Failed to compile tokenizer: {compile_result.stderr}")
    
    def test_multiple_documents(self):
        manifest_path = self.test_dir / "test_multi.csv"
        text_path = self.test_dir / "test_multi.txt"
        
        text_path.write_text("common word", encoding='utf-8')
        
        manifest_lines = [f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n']
        for i in range(1, 4):
            manifest_lines.append(f'{i},test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / f"{i}.html"},{text_path},{text_path.parent / "meta" / f"{i}.json"},abc123,100\n')
        
        manifest_path.write_text(''.join(manifest_lines), encoding='utf-8')
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "common" in terms.lower()
        assert "word" in terms.lower()
    
    def test_statistics_output(self):
        manifest_path = self.test_dir / "test_stats.csv"
        text_path = self.test_dir / "test_stats.txt"
        
        text_path.write_text("hello world hello", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "docs=" in stderr_output
        assert "tokens=" in stderr_output
        assert "unique_terms=" in stderr_output
        assert "avg_token_len=" in stderr_output
    
    def test_zipf_output(self):
        manifest_path = self.test_dir / "test_zipf.csv"
        text_path = self.test_dir / "test_zipf.txt"
        
        text_path.write_text("word1 word2 word1 word2 word3", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        zipf_path = self.test_dir / "zipf.csv"
        assert zipf_path.exists()
        
        zipf_content = zipf_path.read_text(encoding='utf-8')
        assert "rank,freq,zipf_pred" in zipf_content
    
    def test_empty_document(self):
        manifest_path = self.test_dir / "test_empty.csv"
        text_path = self.test_dir / "test_empty.txt"
        
        text_path.write_text("", encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        term_freq_path = self.test_dir / "term_freq.csv"
        terms = term_freq_path.read_text(encoding='utf-8')
        
        assert "term,freq" in terms
    
    def test_large_document(self):
        manifest_path = self.test_dir / "test_large.csv"
        text_path = self.test_dir / "test_large.txt"
        
        large_text = "word " * 10000
        text_path.write_text(large_text, encoding='utf-8')
        
        manifest_path.write_text(
            f'doc_id,source_id,url,final_url,fetch_ts,status,content_type,encoding,bytes_len,raw_path,text_path,meta_path,sha256_text,text_len\n'
            f'1,test,http://example.com,http://example.com,2025-01-01T00:00:00Z,200,text/html,utf-8,100,{text_path.parent / "raw" / "1.html"},{text_path},{text_path.parent / "meta" / "1.json"},abc123,100\n',
            encoding='utf-8'
        )
        
        result = subprocess.run([
            str(self.executable_path),
            "--manifest", str(manifest_path),
            "--out", str(self.test_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        stderr_output = result.stderr
        assert "docs=1" in stderr_output
        assert "tokens=" in stderr_output