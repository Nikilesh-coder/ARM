# ARM — PDF Conversion Provider Comparison Report

**Selected Provider**: `internal`

**Target Output Path**: `C:\Users\A9959\OneDrive\Desktop\ARM\.storage\templates\users\usr_demo_student\templates\1a1ae674-1011-420b-818e-1cf16a667bbd\JAGADEESH PPT_working.docx`

## Provider Evaluation Table

| Provider | Conversion | Pages | Blank Pages | Dimensions | Visual Fidelity | Result |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| cloudconvert | PASS | 17 | 3 | PASS | FAIL | REJECT |
| convertapi | NOT_RUN | N/A | N/A | N/A | N/A | SKIPPED — API key not configured |
| pdfco | NOT_RUN | N/A | N/A | N/A | N/A | SKIPPED — API key not configured |
| internal | PASS | 13 | 0 | PASS | PASS | PASS |

## Detailed Provider Notes

### cloudconvert
- **Status**: `REJECT`
- **Notes/Reasons**:
  - Presentation template page count mismatch: Original has 13 slides, but converted DOCX renders as 17 pages (+4 extra/missing).
  - Converted DOCX introduced 3 blank/near-blank pages: [10, 12, 14]

### convertapi
- **Status**: `SKIPPED — API key not configured`

### pdfco
- **Status**: `SKIPPED — API key not configured`

### internal
- **Status**: `PASS`
