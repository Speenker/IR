from flask import Flask, request
import subprocess
import os
import re
from urllib.parse import quote_plus

INV = "index/inv.bin"
FWD = "index/fwd.bin"
CLI = "./search_cli"      

PAGE_SIZE = 50

def smart_truncate_title(title, max_len=80):
    if len(title) <= max_len:
        return title
    
    truncated = title[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > 30:
        truncated = truncated[:last_space]
    
    return truncated + "..."

app = Flask(__name__)

FORM_HTML = """
<!doctype html>
<meta charset="utf-8">
<title>Boolean / TF-IDF Search</title>
<h2>Boolean / TF-IDF Search</h2>
<form action="/search" method="get">
  <input type="text" name="q" style="width:650px" value="{q}">
  <button type="submit">Search</button>
</form>
<hr>
{body}
"""

def run_query(q: str, offset: int, limit: int):
    if not os.path.exists(INV) or not os.path.exists(FWD):
        return [], f"Index files not found: {INV} or {FWD}"

    if not os.path.exists(CLI) and os.path.exists(CLI + ".exe"):
        cli_path = CLI + ".exe"
    else:
        cli_path = CLI

    p = subprocess.run(
        [cli_path, "--inv", INV, "--fwd", FWD, "--offset", str(offset), "--limit", str(limit)],
        input=(q + "\n").encode("utf-8", errors="ignore"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    out_lines = p.stdout.decode("utf-8", errors="ignore").splitlines()
    err = p.stderr.decode("utf-8", errors="ignore").strip()

    rows = []
    for line in out_lines:
        parts = line.split("\t")
        if len(parts) >= 3:
            if len(parts) >= 4 and parts[1].replace('.', '').replace('-', '').isdigit():
                docid, score, title, url = parts[0], parts[1], parts[2], parts[3]
                rows.append((docid, title, url, score))
            else:
                docid, title, url = parts[0], parts[1], parts[2]
                rows.append((docid, title, url, None))
    return rows, err

@app.get("/")
def home():
    return FORM_HTML.format(q="", body="")

@app.get("/search")
def search():
    q = (request.args.get("q") or "").strip()
    page = int(request.args.get("page") or "0")
    if page < 0:
        page = 0

    if not q:
        return FORM_HTML.format(q="", body="<p>Empty query</p>")

    offset = page * PAGE_SIZE
    rows, err = run_query(q, offset=offset, limit=PAGE_SIZE)

    items = []
    for docid, title, url, score in rows:
        display_title = smart_truncate_title(title)
        
        if score is not None:
            items.append(f'<div><a href="{url}" target="_blank">{display_title}</a> <small>({docid}, score: {score})</small></div>')
        else:
            items.append(f'<div><a href="{url}" target="_blank">{display_title}</a> <small>({docid})</small></div>')

    nav = []
    qurl = quote_plus(q)
    if page > 0:
        nav.append(f'<a href="/search?q={qurl}&page={page-1}">Prev</a>')
    nav.append(f'<a href="/search?q={qurl}&page={page+1}">Next</a>')

    body = ""
    if err:
        body += f"<pre style='color:#666'>{err}</pre>"

    if items:
        body += "\n".join(items)
    else:
        body += "<p>No results</p>"

    body += "<hr>" + " | ".join(nav) + f"<div><small>page={page}, offset={offset}</small></div>"

    return FORM_HTML.format(q=q, body=body)

if __name__ == "__main__":
    app.run("127.0.0.1", 8000, debug=True)
