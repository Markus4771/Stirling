#!/usr/bin/env python3
"""Update the generated AutoSplitPdfRequest interface in a local v3.1.0 checkout.
This is a temporary development helper; final builds must regenerate API types.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.home()/"stirling-qr-gui-src"
path=root/"frontend/editor/src/core/types/toolApiTypes.ts"
data=path.read_text()
old='''export interface AutoSplitPdfRequest {
  /**
   * Flag indicating if the duplex mode is active, where the page after the divider also gets removed.
   */
  duplexMode?: boolean;
}'''
new='''export interface AutoSplitPdfRequest {
  /**
   * Flag indicating if the duplex mode is active, where the page after the divider also gets removed.
   */
  duplexMode?: boolean;
  qrMode?: "standard" | "prefix" | "exact";
  qrValue?: string;
  keepQrPage?: boolean;
}'''
if old not in data:
    raise SystemExit("AutoSplitPdfRequest signature changed: regenerate from OpenAPI instead")
path.write_text(data.replace(old,new,1))
print("Updated generated API model for local prototype:",path)
