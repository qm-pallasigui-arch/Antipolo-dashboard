from pathlib import Path
import re
# Readability-only formatting of newly authored prose; code, links, IDs and hashes stay literal.
words='on September November January December Verified verified and is aged eligible Top pending to Dengue printed weekly workbook difference common burn root tolerance lag maxiter candidates window Table Chapter Figure Python dataset all with these only includes contains covers returned reported passed failed warnings from through train test year years months observations cases reference training evaluation records rows cells series fold version current after before of for at have has in than'.split()
pattern=re.compile(r'\b('+'|'.join(words)+r')(?=\d)')
for name in ['CHATGPT_RETURN_HANDOFF.md','MODEL_EVALUATION.md','TEST_RESULTS.md','DECISION_LEDGER.md']:
 p=Path(name);lines=[];fenced=False
 for line in p.read_text(encoding='utf-8-sig').splitlines():
  if line.startswith('```'):fenced=not fenced;lines.append(line);continue
  if fenced:lines.append(line);continue
  chunks=re.split(r'(`[^`]*`|\[[^\]]*\]\([^)]*\))',line)
  for i,chunk in enumerate(chunks):
   if i%2:continue
   chunk=pattern.sub(r'\1 ',chunk)
   chunk=re.sub(r'(?<=\d)(?=(?:January|December|September|November|seconds|months|years)\b)',' ',chunk)
   chunk=re.sub(r',(?=[A-Za-z0-9])',', ',chunk)
   chunk=re.sub(r':(?=\d)',': ',chunk)
   chunks[i]=chunk
  lines.append(''.join(chunks))
 p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
