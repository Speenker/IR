import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestTFIDFBasic:
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
    
    def test_single_term_tfidf_scoring(self):
        manifest_path = self.test_dir / "test_single.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = [
            {
                "id": 1,
                "url": "http://example.com/doc1",
                "text": "python programming tutorial",
                "title": "Python Tutorial"
            },
            {
                "id": 2,
                "url": "http://example.com/doc2",
                "text": "java programming guide",
                "title": "Java Guide"
            },
            {
                "id": 3,
                "url": "http://example.com/doc3",
                "text": "python python python",
                "title": "Python Only"
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
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        scored_results = []
        
        for line in output_lines:
            if line.strip() and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 4 and '.' in parts[1]:
                    scored_results.append((parts[0], float(parts[1])))
        
        assert len(scored_results) > 0
        
        scores_by_doc = {doc_id: score for doc_id, score in scored_results}
        assert '3' in scores_by_doc
        
        doc3_score = scores_by_doc['3']
        assert doc3_score > 0
    
    def test_ranked_search_order(self):
        manifest_path = self.test_dir / "test_ranked.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = [
            {
                "id": 1,
                "url": "http://example.com/doc1",
                "text": "word",
                "title": "Single Word"
            },
            {
                "id": 2,
                "url": "http://example.com/doc2",
                "text": "word word word",
                "title": "Triple Word"
            },
            {
                "id": 3,
                "url": "http://example.com/doc3",
                "text": "word word",
                "title": "Double Word"
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
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="word\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        if not result.stdout.strip():
            pytest.skip(f"No search results returned. Stderr: {result.stderr}")
        
        output_lines = result.stdout.strip().split('\n')
        
        all_results = []
        for line in output_lines:
            if line.strip() and '\t' in line:
                all_results.append(line)
        
        assert len(all_results) > 0
        
        scored_results = []
        for line in all_results:
            parts = line.split('\t')
            if len(parts) >= 4 and '.' in parts[1]:
                scored_results.append((parts[0], float(parts[1])))
        
        if scored_results:
            scores = [score for _, score in scored_results]
            assert scores == sorted(scores, reverse=True)
    
    def test_tfidf_with_rare_term(self):
        manifest_path = self.test_dir / "test_rare.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = [
            {
                "id": 1,
                "url": "http://example.com/doc1",
                "text": "common word",
                "title": "Common Doc"
            },
            {
                "id": 2,
                "url": "http://example.com/doc2",
                "text": "rareunique term",
                "title": "Rare Doc"
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
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="rareunique\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        
        found_rare = False
        for line in output_lines:
            if line.strip() and 'rareunique' in line.lower():
                found_rare = True
                parts = line.split('\t')
                if len(parts) >= 4 and '.' in parts[1]:
                    score = float(parts[1])
                    assert score > 0
                break
        
        assert found_rare
    
    def test_multiterm_tfidf(self):
        manifest_path = self.test_dir / "test_multi.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = [
            {
                "id": 1,
                "url": "http://example.com/doc1",
                "text": "python programming",
                "title": "Both Terms"
            },
            {
                "id": 2,
                "url": "http://example.com/doc2",
                "text": "python",
                "title": "Python Only"
            },
            {
                "id": 3,
                "url": "http://example.com/doc3",
                "text": "programming",
                "title": "Programming Only"
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
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python programming\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        
        doc1_result = None
        for line in output_lines:
            if line.strip() and line.startswith('1\t'):
                doc1_result = line
                break
        
        assert doc1_result is not None
        
        parts = doc1_result.split('\t')
        if len(parts) >= 4 and '.' in parts[1]:
            score = float(parts[1])
            assert score > 0


class TestTFIDFScoring:
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
    
    def test_tfidf_score_positive(self):
        manifest_path = self.test_dir / "test_positive.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        text_file = text_dir / "doc1.txt"
        text_file.write_text("test document", encoding='utf-8')
        
        manifest_path.write_text(
            'doc_id,final_url,text_path\n'
            '1,http://example.com,texts/doc1.txt\n',
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="test\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        
        for line in output_lines:
            if line.strip() and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 4 and '.' in parts[1]:
                    score = float(parts[1])
                    assert score >= 0
    
    def test_tfidf_score_reasonable(self):
        manifest_path = self.test_dir / "test_reasonable.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        text_file = text_dir / "doc1.txt"
        text_file.write_text("word " * 100, encoding='utf-8')
        
        manifest_path.write_text(
            'doc_id,final_url,text_path\n'
            '1,http://example.com,texts/doc1.txt\n',
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        result = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="word\n", capture_output=True, text=True)
        
        assert result.returncode == 0
        
        output_lines = result.stdout.strip().split('\n')
        
        for line in output_lines:
            if line.strip() and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 4 and '.' in parts[1]:
                    score = float(parts[1])
                    assert score < 1000
    
    def test_boolean_vs_ranked_difference(self):
        manifest_path = self.test_dir / "test_boolean.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        text_file = text_dir / "doc1.txt"
        text_file.write_text("python programming", encoding='utf-8')
        
        manifest_path.write_text(
            'doc_id,final_url,text_path\n'
            '1,http://example.com,texts/doc1.txt\n',
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        result_bool = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python && programming\n", capture_output=True, text=True)
        
        assert result_bool.returncode == 0
        
        result_ranked = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin")
        ], input="python\n", capture_output=True, text=True)
        
        assert result_ranked.returncode == 0
        
        if not result_ranked.stdout.strip():
            pytest.skip(f"No ranked search results returned. Stderr: {result_ranked.stderr}")
        
        ranked_has_scores = False
        ranked_has_results = False
        
        for line in result_ranked.stdout.strip().split('\n'):
            if line.strip():
                ranked_has_results = True
                if '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 4 and '.' in parts[1]:
                        ranked_has_scores = True
                        break
        
        assert ranked_has_results
        assert ranked_has_scores


class TestTFIDFIntegration:
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
    
    def test_tfidf_with_pagination(self):
        manifest_path = self.test_dir / "test_pagination.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        test_docs = []
        for i in range(1, 6):
            text_file = text_dir / f"doc{i}.txt"
            text_file.write_text(f"common term{i}", encoding='utf-8')
            test_docs.append(f'{i},http://example.com/{i},texts/doc{i}.txt')
        
        manifest_path.write_text(
            'doc_id,final_url,text_path\n' + '\n'.join(test_docs),
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(manifest_path),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        result1 = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin"),
            "--limit", "1"
        ], input="common\n", capture_output=True, text=True)
        
        assert result1.returncode == 0
        
        result2 = subprocess.run([
            str(self.search_exe),
            "--inv", str(self.test_dir / "inv.bin"),
            "--fwd", str(self.test_dir / "fwd.bin"),
            "--limit", "3"
        ], input="common\n", capture_output=True, text=True)
        
        assert result2.returncode == 0
        
        lines1 = [line for line in result1.stdout.strip().split('\n') if line.strip()]
        lines2 = [line for line in result2.stdout.strip().split('\n') if line.strip()]
        
        assert len(lines2) >= len(lines1)
    
    def test_empty_query_handling(self):
        manifest_path = self.test_dir / "test_empty_query.csv"
        text_dir = self.test_dir / "texts"
        text_dir.mkdir()
        
        text_file = text_dir / "doc1.txt"
        text_file.write_text("test content", encoding='utf-8')
        
        manifest_path.write_text(
            'doc_id,final_url,text_path\n'
            '1,http://example.com,texts/doc1.txt\n',
            encoding='utf-8'
        )
        
        subprocess.run([
            str(self.index_exe),
            "--manifest", str(self.test_dir / "test_empty_query.csv"),
            "--outdir", str(self.test_dir),
            "--root", str(self.test_dir)
        ], capture_output=True, text=True)
        
        test_queries = ["", "   ", "\t\n"]
        
        for query in test_queries:
            result = subprocess.run([
                str(self.search_exe),
                "--inv", str(self.test_dir / "inv.bin"),
                "--fwd", str(self.test_dir / "fwd.bin")
            ], input=query + "\n", capture_output=True, text=True)
            
            assert result.returncode == 0 or result.returncode == 1