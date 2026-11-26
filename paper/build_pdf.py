"""Build the English paper on Windows: python paper/build_pdf.py [team-number]."""
from pathlib import Path
import re
import sys
import textwrap
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table,
    TableStyle, KeepTogether, PageBreak, Preformatted)
from reportlab.platypus.tableofcontents import TableOfContents

paper = Path(__file__).resolve().parent
root = paper.parent
team = sys.argv[1] if len(sys.argv)>1 else "PENDING"
if not re.fullmatch(r"[A-Za-z0-9]+", team):
    raise ValueError("Use the registered team identifier")
out = root / "output/pdf"
out.mkdir(parents=True, exist_ok=True)
file = out / ("B-review.pdf" if team=="PENDING" else f"B{team}.pdf")
for name, font in [('Body','arial.ttf'),('Head','arialbd.ttf'),('Code','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts')/font)))
style = lambda n,f,size,leading: ParagraphStyle(n,fontName=f,fontSize=size,leading=leading,spaceAfter=7)
body=style("body","Body",11,15)
head=style("heading","Head",16,20)
sub=style("sub","Head",12,16)
caption=style("caption","Body",9,12)
small=style("small","Body",8,10)
mono=style("code","Code",7,9)
def paragraph(value, form=body):
    value=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',value).replace('**','').strip('*')
    return Paragraph(escape(value),form)

class Paper(SimpleDocTemplate):
    def afterFlowable(self, item):
        if isinstance(item,Paragraph) and item.style in (head,sub):
            name=item.getPlainText()
            if name not in ('Summary','Contents'):
                self.notify('TOCEntry',(int(item.style==sub),name,self.page))

doc=Paper(str(file),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=48,bottomMargin=44,
          title="Reconstructing Converter Flame Spectra and Forecasting Delayed Flue-Gas Measurements",author="APMCM Team")
story=[]
lines=(paper/'manuscript-en.md').read_text(encoding='utf-8-sig').splitlines()
i=0
while i<len(lines):
    line=lines[i].strip()
    i+=1
    if not line:continue
    if line.startswith('# '):
        story.append(paragraph(line[2:],style("title","Head",21,25)))
    elif line=='## Contents':
        toc=TableOfContents()
        toc.levelStyles=[style("entry","Body",11,17),style("child","Body",10,14)]
        story.extend([PageBreak(),paragraph("Contents",head),Spacer(1,12),toc])
        while i<len(lines) and not lines[i].startswith('## '):i+=1
    elif line.startswith('## '):
        if line.startswith(('## 1.', '## 2.', '## 6.')):story.append(PageBreak())
        if line.startswith('## 6.'):
            story.extend([paragraph('References',head),
                paragraph('[1] APMCM Organizing Committee. Problem B: Dual-modal Temporal Information Fusion Modeling for Converter Steelmaking Process and Attachments 1–10. 2026.'),
                paragraph('[2] F. N. Fritsch and J. Butland. A Method for Constructing Local Monotone Piecewise Cubic Interpolants. SIAM Journal on Scientific and Statistical Computing, 5(2), 1984, pp. 300–304. DOI 10.1137/0905021.'),
                paragraph('[3] A. E. Hoerl and R. W. Kennard. Ridge Regression: Biased Estimation for Nonorthogonal Problems. Technometrics, 12(1), 1970, pp. 55–67. DOI 10.1080/00401706.1970.10488634.'),PageBreak()])
        story.append(paragraph(line[3:],head))
    elif line.startswith('### '):
        if not line.startswith('### 6.1'):story.append(PageBreak())
        story.append(paragraph(line[4:],sub))
    elif line.startswith('|'):
        rows=[]
        while True:
            cells=line.strip('|').split('|')
            if not all(re.fullmatch(r'[-: ]+',x) for x in cells):
                rows.append([paragraph(x.strip(),small) for x in cells])
            if i==len(lines) or not lines[i].startswith('|'):break
            line=lines[i];i+=1
        table=Table(rows,colWidths=[(doc.width-12)/len(rows[0])]*len(rows[0]),repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dee9ee')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f8')])]))
        story.append(table)
    elif line.startswith('!['):
        path=re.search(r'\]\((.*?)\)',line)[1]
        img=Image(str(paper/path))
        scale=min((doc.width-12)/img.imageWidth, (600 if 'predictions_10s' in path else 300)/img.imageHeight)
        img.drawWidth=img.imageWidth*scale;img.drawHeight=img.imageHeight*scale
        while i<len(lines) and not lines[i].strip():i+=1
        group=[img]
        if i<len(lines) and lines[i].startswith('*Figure'):
            group.append(paragraph(lines[i],caption));i+=1
        story.append(KeepTogether(group))
    else:
        line=line.replace('Each attachment supplies','Each attachment [1] supplies').replace('monotone piecewise cubic Hermite curve to','monotone piecewise cubic Hermite curve [2] to').replace('Ridge models are standardized','Ridge models [3] are standardized')
        story.append(paragraph(line,caption if line.startswith('*Table') else body))
story.extend([PageBreak(),paragraph('7. Software and source listings',head),
              paragraph('Python was used for data extraction, numerical reconstruction, regression and plotting. Dependencies include NumPy, pyxlsb, Pillow, Matplotlib and ReportLab. Listings below are grouped by repository path.')])
for folder in ('B_audit','q1_q2','q3','question3','paper'):
    for source in sorted((root/folder).glob('*.py')):
        if source.name=='build_pdf.py':continue
        story.append(paragraph(source.relative_to(root).as_posix(),caption))
        rendered=[]
        for line in source.read_text(encoding='utf-8-sig').splitlines():
            line = re.sub(r'[\u3000-\u9fff\uff00-\uffef]', lambda m: ascii(m[0])[1:-1], line)
            rendered.extend(textwrap.wrap(line.expandtabs(4),width=110,replace_whitespace=False,drop_whitespace=False) or [''])
        for start in range(0,len(rendered),30):
            story.append(Preformatted('\n'.join(rendered[start:start+30]),mono))
def header(canvas, doc):
    canvas.setFont('Body',9)
    canvas.drawString(45,A4[1]-28,'Team '+team)
    canvas.drawRightString(A4[0]-45,A4[1]-28,'Page '+str(doc.page))
doc.multiBuild(story,onFirstPage=header,onLaterPages=header)
print(file)
