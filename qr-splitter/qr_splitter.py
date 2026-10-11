#!/usr/bin/env python3
"""Trennt PDFs nur bei QR-Codes mit einem festgelegten Präfix (Standard SCAN:)."""
import argparse, fcntl, logging, os, re, tempfile, time, uuid
from pathlib import Path
import cv2, fitz, numpy as np

def read_qr(page, prefix):
    pix = page.get_pixmap(matrix=fitz.Matrix(2,2), colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height,pix.width,3)
    scanner = cv2.QRCodeDetector()
    found, values, _, _ = scanner.detectAndDecodeMulti(rgb)
    result = [v for v in values if v.startswith(prefix)] if found else []
    if not result:
        value, _, _ = scanner.detectAndDecode(rgb)
        if value.startswith(prefix): result = [value]
    return sorted(set(result))

def process(source, output, prefix, dry_run):
    if source.is_symlink() or not source.is_file() or source.suffix.lower() != ".pdf": return
    original = source.stat()
    if time.time()-original.st_mtime < 30: return
    with fitz.open(source) as pdf:
        if pdf.needs_pass: raise ValueError("Verschlüsselte PDF")
        starts=[]
        for i,page in enumerate(pdf):
            codes=read_qr(page,prefix)
            if len(codes)>1: raise ValueError(f"Mehrere passende QR-Codes auf Seite {i+1}")
            if codes: starts.append((i,re.sub(r"[^\w.-]+","_",codes[0][len(prefix):]).strip("._")[:60] or "Dokument"))
        if not starts:
            logging.info("Kein Trenncode: %s (bleibt liegen)", source.name)
            return
        segments=[]
        if starts[0][0]>0: segments.append((0,starts[0][0],"Ohne_QR"))
        for i,(start,label) in enumerate(starts):
            end=starts[i+1][0] if i+1<len(starts) else len(pdf)
            segments.append((start,end,label))
        logging.info("%s: %d Dokumente",source.name,len(segments))
        if dry_run: return
        with tempfile.TemporaryDirectory(dir=output,prefix=".qr-work-") as tmp:
            prepared=[]
            for i,(start,end,label) in enumerate(segments,1):
                part=fitz.open()
                part.insert_pdf(pdf,from_page=start,to_page=end-1)
                dest=Path(tmp)/f"{source.stem}_{i:03d}_{label}.pdf"
                part.save(dest,garbage=3,deflate=True)
                part.close()
                prepared.append(dest)
            current=source.stat()
            if (original.st_size,original.st_mtime_ns)!=(current.st_size,current.st_mtime_ns):
                raise RuntimeError("Quelldatei hat sich verändert")
            published=[]
            try:
                for part in prepared:
                    dest=output/f"{uuid.uuid4().hex[:12]}_{part.name}"
                    os.replace(part,dest)
                    published.append(dest)
                archive=source.parent/"_archiv"
                archive.mkdir(exist_ok=True)
                os.replace(source,archive/f"{uuid.uuid4().hex[:12]}_{source.name}")
            except Exception:
                logging.error("Teilweise ausgegebene Dateien vor Wiederholung kontrollieren: %s",published)
                raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("/srv/samba-shares/Scan-QR"))
    p.add_argument("--destination",type=Path,default=Path("/srv/samba-shares/Scan-Eingang"))
    p.add_argument("--prefix",default="SCAN:")
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    if not a.prefix or not a.source.is_dir() or not a.destination.is_dir() or a.source.resolve()==a.destination.resolve():
        p.error("Quell-/Zielordner und ein Präfix erforderlich; Quelle und Ziel müssen verschieden sein")
    with open("/tmp/stirling-qr-splitter.lock","a+") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return
        errors=0
        for file in sorted(a.source.iterdir()):
            try: process(file,a.destination,a.prefix,a.dry_run)
            except Exception:
                logging.exception("Fehler bei %s",file)
                errors+=1
        if errors: raise SystemExit(1)

if __name__=="__main__": main()
