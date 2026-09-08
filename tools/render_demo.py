"""Render captioned demonstration slides from a completed, genuine CLI run."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'outputs' / 'demo-video'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def slide(number, title, subtitle, lines, caption):
    im = Image.new('RGB', (1280,720), '#111b2a')
    d = ImageDraw.Draw(im)
    def text(x,y,value,size=26,color='#e5edf6',mono=False):
        d.text((x,y),value,font=ImageFont.truetype(MONO if mono else FONT,size),fill=color)
    d.rectangle((0,0,1280,8), fill='#55d8be')
    text(60,35,'IMPORT REVIEW  /  AGENTS FOR HUMANS',18,'#55d8be')
    text(60,90,title,42)
    text(60,151,subtitle,23,'#a5b9cf')
    d.rounded_rectangle((50,210,1230,580),radius=14,fill='#1b2a3e')
    for i,line in enumerate(lines):
        text(75,232+i*49,line,25,mono=True)
    text(60,620,caption,21,'#c0d0df')
    text(1150,666,f'{number:02d}/08',17,'#829bb3')
    path=DEST/f'slide-{number:02d}.png';im.save(path)
    return path

def main():
    execution=json.loads((ROOT/'examples/demo-run/execution.json').read_text())
    assert execution['exit_code']==0 and execution['repeat']['exit_code']==0
    assert not execution['repeat']['stdout']
    job=ROOT/'examples/demo-run/artifacts'
    manifest=json.loads((job/'manifest.json').read_text())
    trace=json.loads((job/'agent-trace.json').read_text())
    review=json.loads((job/'review.json').read_text())
    assert manifest['accepted']==1 and manifest['review']==3
    tools=[x['tool'] for x in trace['tool_results']]
    assert set(tools)=={'read_policy','inspect_csv','propose_mapping','validate_import','export_result'}
    DEST.mkdir(parents=True, exist_ok=True)
    slides=[
      ('Supplier imports, with evidence', 'A Strands agent for small inventory and operations teams',
       ['Every supplier sends a slightly different CSV.', 'Clean rows should not wait for manual retyping.', 'Uncertain rows should not silently enter inventory.', '', 'Read policy. Validate. Export. Keep the evidence.'],
       'A local working prototype, demonstrated with synthetic supplier data.',16),
      ('Why this task matters', 'For the person repeatedly cleaning supplier inventory files',
       ['Header aliases change: Code, Qty, Price.', 'A quantity can be negative or malformed.', 'Two records can disagree about the same SKU.', '', 'Goal: automate the routine path; expose exceptions.'],
       'No customer deployment or measured time-saving claim is implied.',18),
      ('One bounded workflow', 'Strands selects the tools; validation enforces the supplier policy',
       ['CSV + policy -> frozen inbox job', '             -> Strands + tool-capable model', '             -> inspect -> map -> validate -> export', '', 'accepted.csv | review.json | manifest + tool trace'],
       'Tools have bound inputs and outputs, with no shell or arbitrary file access.',20),
      ('The actual input', 'Documented aliases map Code / Qty / Price to canonical fields',
       (ROOT/'examples/demo-run/supplier.csv').read_text().splitlines(),
       'Trimming and uppercasing are explicitly permitted by the policy.',18),
      ('A fresh CLI run', 'Actual CLI invocation and tool activity; model waiting omitted',
       ['python inbox.py <inbox> <policy> <outputs>', '  --state <state.json> --model devin-free/glm-5-2', '  --base-url http://127.0.0.1:9020/v1', '', 'read_policy -> inspect_csv -> propose_mapping', 'validate_import -> export_result'],
       f"Strands 1.54.0 | Actual elapsed time: {execution['elapsed_seconds']:.1f}s | Exit code: 0",24),
      ('One accepted, three for review', 'These values come from the exported artifacts',
       ['accepted.csv: 001AB,2,1.2300', '', 'Row 3 / B20: negative quantity', 'Row 4 / C30: conflicting duplicate SKU', 'Row 5 / C30: conflicting duplicate SKU', '4 input rows = 1 accepted + 3 review'],
       'Original values and record numbers remain available in the review queue.',23),
      ('Run it again: no duplicate work', 'A second real CLI process used the same input and persistent state',
       ['First run:  status = complete', 'Second run: exit code = 0; no new job event', '', 'Content fingerprint = source bytes + policy', 'Output hashes are verified before completion.'],
       'Failed or interrupted jobs require an explicit retry.',18),
      ('Inspect, run, extend', 'Public MIT source with setup instructions and 20 passing tests',
       ['github.com/DITlieD/import-review', '', 'Python CLI + Strands; configurable model provider', 'Actual tool transcript included for inspection', 'Next: richer supplier policies and operator review'],
       'Ambiguous records stay in review until an operator resolves them.',18),
    ]
    paths=[]
    for i,(title,sub,lines,caption,duration) in enumerate(slides,1):
        paths.append((slide(i,title,sub,lines,caption),duration))
    concat=DEST/'frames.txt'
    concat.write_text(''.join(f"file '{p.name}'\nduration {dur}\n" for p,dur in paths)+f"file '{paths[-1][0].name}'\n")
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-vf','fps=24','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(DEST/'import-review-demo.mp4')],check=True)
    print(DEST/'import-review-demo.mp4')

if __name__=='__main__': main()
