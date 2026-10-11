#!/usr/bin/env python3
"""Apply the QR GUI prototype to an existing clean Stirling PDF v3.1.0 checkout.
Uses exact text anchors instead of brittle unified-diff line contexts.
Never touches an installed JAR or running service.
"""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.home() / "stirling-qr-gui-src"
files = {
    "request": "app/core/src/main/java/stirling/software/SPDF/model/api/misc/AutoSplitPdfRequest.java",
    "controller": "app/core/src/main/java/stirling/software/SPDF/controller/api/misc/AutoSplitPdfController.java",
    "params": "frontend/editor/src/core/hooks/tools/split/useSplitParameters.ts",
    "settings": "frontend/editor/src/core/components/tools/split/SplitSettings.tsx",
    "operation": "frontend/editor/src/core/hooks/tools/split/useSplitOperation.ts",
    "api": "frontend/editor/src/core/types/toolApiTypes.ts",
}
original = {k:(root/v).read_text() for k,v in files.items()}
changed = dict(original)

def rep(key, old, new):
    s = changed[key]
    if s.count(old) != 1:
        raise RuntimeError(f"{key}: anchor found {s.count(old)} times: {old[:90]!r}")
    changed[key] = s.replace(old, new, 1)

rep("request", "    private Boolean duplexMode;","""    private Boolean duplexMode;

    @Schema(description = "QR matching mode: standard, prefix, exact")
    private String qrMode = "standard";

    @Schema(description = "QR content or prefix for custom matching")
    private String qrValue;

    @Schema(description = "Keep the page containing the separator QR")
    private Boolean keepQrPage = false;""")

rep("controller", '        boolean duplexMode = Boolean.TRUE.equals(request.getDuplexMode());', '''        boolean duplexMode = Boolean.TRUE.equals(request.getDuplexMode());
        String qrMode = request.getQrMode() == null ? "standard" : request.getQrMode();
        if (!Set.of("standard", "prefix", "exact").contains(qrMode)) {
            throw new IllegalArgumentException("Invalid QR match mode");
        }
        String qrValue = request.getQrValue();
        if (!"standard".equals(qrMode)
                && (qrValue == null || qrValue.isBlank() || qrValue.length() > 256)) {
            throw new IllegalArgumentException("QR value must be 1-256 characters");
        }
        boolean keepQrPage = Boolean.TRUE.equals(request.getKeepQrPage());
        if (keepQrPage && duplexMode) {
            throw new IllegalArgumentException("Cannot keep QR page while using duplex removal");
        }''')
rep("controller",'boolean isValidQrCode = qrResult != null && VALID_QR_CONTENTS.contains(qrResult);','''boolean isValidQrCode = qrResult != null
                        && switch (qrMode) {
                            case "prefix" -> qrResult.startsWith(qrValue);
                            case "exact" -> qrResult.equals(qrValue);
                            default -> VALID_QR_CONTENTS.contains(qrResult);
                        };''')
rep("controller",'if (!splitDocuments.isEmpty() && !isValidQrCode) {','if (!splitDocuments.isEmpty() && (!isValidQrCode || keepQrPage)) {')

rep("params", '  duplexMode: boolean;', '''  duplexMode: boolean;
  qrMode: "standard" | "prefix" | "exact";
  qrValue: string;
  keepQrPage: boolean;''')
rep("params", '  duplexMode: false,', '''  duplexMode: false,
  qrMode: "standard",
  qrValue: "SCAN:",
  keepQrPage: false,''')
rep("params", '    case SPLIT_METHODS.BY_PAGE_DIVIDER:\n      return true; // No required parameters', '''    case SPLIT_METHODS.BY_PAGE_DIVIDER:
      return (params.qrMode === "standard" ||
        (params.qrValue.trim().length > 0 && params.qrValue.length <= 256))
        && !(params.keepQrPage && params.duplexMode);''')

rep("settings", '  const renderByPageDividerForm = () => (\n    <Stack gap="sm">', '''  const renderByPageDividerForm = () => (
    <Stack gap="sm">
      <Select
        label="QR-Code-Erkennung"
        value={parameters.qrMode || "standard"}
        data={[
          { value: "standard", label: "Offizieller Stirling-Code" },
          { value: "prefix", label: "Eigenes Präfix" },
          { value: "exact", label: "Exakter QR-Code-Inhalt" },
        ]}
        onChange={(value) =>
          onParameterChange("qrMode", (value || "standard") as "standard" | "prefix" | "exact")
        }
        disabled={disabled}
      />
      {parameters.qrMode !== "standard" && (
        <TextInput
          label="QR-Code-Inhalt oder Präfix"
          value={parameters.qrValue}
          placeholder="SCAN:"
          onChange={(e) => onParameterChange("qrValue", e.target.value)}
          disabled={disabled}
        />
      )}
      <Checkbox
        label="QR-Code-Seite behalten"
        checked={parameters.keepQrPage}
        onChange={(e) => onParameterChange("keepQrPage", e.currentTarget.checked)}
        disabled={disabled || parameters.duplexMode}
      />''')

rep("operation", 'return { duplexMode: parameters.duplexMode ?? false };', '''return {
        duplexMode: parameters.duplexMode ?? false,
        qrMode: parameters.qrMode || "standard",
        qrValue: parameters.qrValue || "",
        keepQrPage: parameters.keepQrPage ?? false,
      };''')
rep("operation", '      duplexMode: apiParams.duplexMode ?? false,', '''      duplexMode: apiParams.duplexMode ?? false,
      qrMode: apiParams.qrMode ?? "standard",
      qrValue: apiParams.qrValue ?? "SCAN:",
      keepQrPage: apiParams.keepQrPage ?? false,''')

rep("api", '  duplexMode?: boolean;\n}\nexport interface BatchAttachmentRequest', '''  duplexMode?: boolean;
  qrMode?: "standard" | "prefix" | "exact";
  qrValue?: string;
  keepQrPage?: boolean;
}
export interface BatchAttachmentRequest''')

# Validate everything first; fail without writing partial modifications.
for key, value in changed.items():
    if value == original[key]:
        raise RuntimeError(f"No changes produced: {key}")
for key, path in files.items():
    (root / path).write_text(changed[key])
print("Modified six Stirling v3.1.0 source files:")
for path in files.values():
    print("  ", path)
