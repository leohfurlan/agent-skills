"""Esqueleto: re-derive cada afirmação numérica de um relatório e compare com o que o documento diz.

Uso: copie para %TEMP%/hermes-verify-<assunto>.py, adapte as seções marcadas com TODO e rode.
Preserve o resultado em output/<...>/verificar-relatorio.py; apague a cópia do temp no fim.
Status: verificação AD-HOC, não suíte canônica. Rótulo isso explicitamente ao reportar.
"""
import hashlib, json, os, re, subprocess, sys, unicodedata

ROOT = r"C:\caminho\do\projeto"          # TODO
REPORT = os.path.join(ROOT, "docs", "relatorio.md")   # TODO
OUT = os.path.join(ROOT, "output", "qa")

ok, fail, warn = [], [], []
def check(nome, cond, detalhe=""):
    (ok if cond else fail).append(f"{nome} :: {detalhe}")

txt = open(REPORT, encoding="utf-8").read()

# ---------- 1. integridade do documento ----------
check("cercas de código balanceadas", txt.count("```") % 2 == 0, f"{txt.count('```')} ocorrências")
check("sem marcador de truncamento", "[truncated]" not in txt and "!!" not in txt)
ruins = []
for bloco in re.split(r"\n\s*\n", txt):
    linhas = [l for l in bloco.splitlines() if l.strip().startswith("|")]
    if len(linhas) >= 2 and len({l.count("|") for l in linhas}) > 1:
        ruins.append(linhas[0][:60])
check("tabelas com colunas consistentes", not ruins, str(ruins[:3]))

# ---------- 2. evidências citadas existem ----------
for rel in ["output/qa/sweep.json"]:      # TODO: liste os arquivos que o relatório cita
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    check("existe " + rel, os.path.exists(p), f"{os.path.getsize(p) if os.path.exists(p) else 0} bytes")

# ---------- 3. contagens de código (do parser, nunca da memória) ----------
def conta(predicado, bases):
    n = 0
    for base in bases:
        for dp, _, fs in os.walk(os.path.join(ROOT, base)):
            for f in fs:
                if predicado(f):
                    n += 1
    return n

rotas = conta(lambda f: f.endswith(".tsx"), ["mobile/app"])            # TODO
check("N arquivos de rota", rotas == 13, f"{rotas}")                   # TODO: número esperado

def ocorrencias(padrao, bases, exts=(".ts", ".tsx")):
    total, arquivos = 0, set()
    for base in bases:
        for dp, _, fs in os.walk(os.path.join(ROOT, base)):
            for f in fs:
                if f.endswith(exts):
                    n = len(re.findall(padrao, open(os.path.join(dp, f), encoding="utf-8").read()))
                    total += n
                    if n: arquivos.add(f)
    return total, arquivos
alertas, arqs = ocorrencias(r"Alert\.alert\(", ["mobile/src"])         # TODO
check("N chamadas de X", alertas == 14, f"{alertas} em {len(arqs)} arquivos")

# LOC: mesma convenção dos dois lados (wc -l == count("\n"))
loc = 0
for base in ["mobile/src", "mobile/app"]:                              # TODO
    for dp, _, fs in os.walk(os.path.join(ROOT, base)):
        for f in fs:
            if f.endswith((".ts", ".tsx")):
                loc += open(os.path.join(dp, f), encoding="utf-8").read().count("\n")
check("N linhas TypeScript (wc -l)", loc == 3741, f"{loc}")             # TODO

# ---------- 4. percentual de paridade (recálculo, não releitura) ----------
def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

def textos_do_mockup(no, out=None):
    out = [] if out is None else out
    if no.get("type") == "text" and no.get("content"): out.append(no["content"])
    for c in no.get("children") or []: textos_do_mockup(c, out)
    return out

# PARES = [(nome_do_frame, texto_renderizado_no_app), ...]   # TODO: use as capturas CORRETAS
# tot = sum(len(list(dict.fromkeys(textos_do_mockup(f)))) for f, _ in PARES)
# pres = sum(sum(1 for t in dict.fromkeys(textos_do_mockup(f)) if norm(t) in norm(tx)) for f, tx in PARES)
# cob = round(100 * pres / tot, 1)
# print(f"[info] cobertura recalculada = {cob}% ({pres}/{tot})")
# check("relatório cita o percentual recalculado", f"{cob}".replace('.', ',') in txt, f"{cob}%")

# ---------- 5. fonte viva (API/schema) ----------
try:
    import urllib.request
    body = urllib.request.urlopen("http://host:8000/api/schema/", timeout=25).read().decode()
    paths = re.search(r"^paths:\n(.*?)^[a-z]+:", body, re.S | re.M).group(1)
    ops = sum(len(re.findall(r"^\s{4}(get|post|put|patch|delete):", b, re.M))
              for b in re.split(r"^  /", paths, flags=re.M)[1:])
    check("N operações de API no schema", ops == 24, f"{ops}")          # TODO
except Exception as e:
    warn.append(f"schema inacessível (aviso, não passa): {e}")

# ---------- 6. suíte de testes de verdade ----------
try:
    r = subprocess.run(["python", "-m", "pytest", "-q"], cwd=os.path.join(ROOT, "backend"),
                       capture_output=True, text=True, timeout=600)
    saida = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""
    check("pytest = 67 passed", "67 passed" in saida and "failed" not in saida, saida[:120])
except Exception as e:
    warn.append(f"pytest não executável: {e}")

# ---------- 7. estado do banco após limpeza ----------
try:
    code = ("from apps.events.models import Event\n"
            "print(Event.objects.count())\n"
            "print('QA-ARTIFACT' if Event.objects.filter(name__icontains='QA ').exists() else 'LIMPO')\n")
    r = subprocess.run(["docker", "exec", "<container>", "python", "manage.py", "shell", "-c", code],
                       capture_output=True, text=True, timeout=180)
    linhas = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    numerica = [l for l in linhas if re.fullmatch(r"[\d\s]+", l)] or [""]
    nums = [int(x) for x in numerica[0].split()]
    check("estado do seed preservado", nums == [3] and any("LIMPO" in l for l in linhas), f"{nums} {linhas[-1:]}")
except Exception as e:
    warn.append(f"checagem do banco falhou: {e}")

# ---------- 8. arquivos espelhados (ex.: skill instalada x repositório) ----------
for rel in ["SKILL.md"]:                                               # TODO
    a, b = os.path.join(ROOT, "skills", rel), os.path.join(ROOT, "..", "repo", rel)
    ha = hashlib.sha256(open(a, "rb").read()).hexdigest() if os.path.exists(a) else "ausente"
    hb = hashlib.sha256(open(b, "rb").read()).hexdigest() if os.path.exists(b) else "ausente"
    check(f"espelhado: {rel}", ha == hb and ha != "ausente", f"{ha[:12]} / {hb[:12]}")

# ---------- resumo ----------
print("=== PASS (%d) ===" % len(ok))
for x in ok: print("  +", x)
if fail:
    print("=== FAIL (%d) — corrija o DOCUMENTO e rode de novo ===" % len(fail))
    for x in fail: print("  -", x)
if warn:
    print("=== AVISOS (%d) ===" % len(warn))
    for x in warn: print("  !", x)
print("\nRESULTADO:", "TODAS AS CHECAGENS PASSARAM" if not fail else f"{len(fail)} FALHA(S)")
sys.exit(1 if fail else 0)
