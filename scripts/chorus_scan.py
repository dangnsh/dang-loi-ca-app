import pdfplumber, re, glob
# scan a sample of PDFs for chorus markers in the text layer
terms=['ĐK','Điệp khúc','Điệp','Chorus','chorus','ĐIỆP KHÚC','ĐK:']
for f in ['/tmp/dlc/public/sheets/DLC_001_An_Chua_day_day.pdf',
          '/tmp/dlc/public/sheets/DLC_002_Bai_ca_dang_Chua.pdf',
          '/tmp/dlc/public/sheets/DLC_050_*.pdf',
          '/tmp/dlc/public/sheets/DLC_027_Chi_an_dien_Chua.pdf']:
    for fn in glob.glob(f):
        hits=[]
        with pdfplumber.open(fn) as p:
            for pi,pg in enumerate(p.pages):
                txt=pg.extract_text() or ''
                for t in terms:
                    if t in txt:
                        hits.append((pi,t))
        print(fn.split('/')[-1], hits[:10])
