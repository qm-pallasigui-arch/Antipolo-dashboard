"""Package only reviewed workspace files; never resets or modifies Git history."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,re
root=Path.cwd()
archive=root/'Antipolo-dashboard-reconciled-2026-09-27.zip'
manifest=root/'reconciliation/delivery-manifest.json'
status=root/'reconciliation/final-git-status.txt'
patch=root/'reconciliation/final-working-tree.patch'
verification=root/'reconciliation/package-verification.json'
for path in (archive,manifest,status,patch,verification,Path(str(archive)+".sha256")):
 if not path.exists():path.write_bytes(b'')
status.write_bytes(subprocess.check_output(['git','status','--porcelain=v1']))
patch.write_bytes(subprocess.check_output(['git','diff','--binary']))
subprocess.run(['python','reconciliation/build_handoff.py'],check=True)
p=root/'docs/archive/CHATGPT_RETURN_HANDOFF.md'
s=p.read_text(encoding='utf-8')
s=s.replace('- Final Git status: see reconciliation/final-git-status.txt and the final-state inventory below. Existing uncommitted changes were not reset, cleaned, committed, or discarded.', '- Final Git status follows (also retained in reconciliation/final-git-status.txt). Existing uncommitted changes were not reset, cleaned, committed, or discarded.\n\n```text\n'+status.read_text(encoding='utf-8').strip()+'\n```')
s=re.sub(r'^## (?!20\.)','### ',s,flags=re.M)
s=s.replace('## 20.10 Remaining decisions\n','## 20.10 Remaining decisions\n\nThe following is a synchronized delivery snapshot of the single authoritative docs/archive/DECISION_LEDGER.md, not an independently maintained ledger.\n')
p.write_text(s,encoding='utf-8')
subprocess.run(['python','reconciliation/format_reports.py'],check=True)
subprocess.run(['git','bundle','verify','reconciliation/repository-history.bundle'],check=True,capture_output=True)
exclude={archive.name,'delivery-manifest.json','package-verification.json',archive.name+'.sha256'}
files=[f for f in sorted(root.rglob('*')) if f.is_file() and not any(x in f.relative_to(root).parts for x in ('.git','__pycache__','.pytest_cache','.browser-tools','.browser-cache')) and f.name not in exclude]
hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest.write_text(json.dumps({'excluded':['.git','__pycache__','.pytest_cache','archive/self-hashes'],'sha256':hashes},indent=2),encoding='utf-8')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files+[manifest]:z.write(f,f.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 assert all(f'## 20.{n} ' in z.read('docs/archive/CHATGPT_RETURN_HANDOFF.md').decode() for n in range(1,13))
 for required in ['TEST_RESULTS.md','docs/archive/MODEL_EVALUATION.md','docs/archive/MANUSCRIPT_REVISION_PROPOSALS.md','docs/archive/DATA_RECONCILIATION.md','docs/archive/AUDIT_MATRIX.md','docs/archive/DECISION_LEDGER.md','reconciliation/baseline.zip','reconciliation/repository-history.bundle']:
  assert required in z.namelist(),required
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
Path(str(archive)+'.sha256').write_text(sha+'  '+archive.name+'\n',encoding='ascii')
verification.write_text(json.dumps({'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha,'files':len(files)+1,'zip_crc':'passed','member_hashes':'passed','git_history_bundle':'verified','required_handoff_sections':12},indent=2),encoding='utf-8')
print(verification.read_text())
