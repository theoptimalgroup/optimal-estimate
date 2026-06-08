.PHONY: import-xlsx-rules-dry import-xlsx-rules

## Dry-run: parse XLSX and show counts without writing to DB.
import-xlsx-rules-dry:
	./scripts/local_import_xlsx_rules.sh --dry-run

## Full import: overwrite existing client/trade rules from XLSX (prompts for backup confirmation).
import-xlsx-rules:
	./scripts/local_import_xlsx_rules.sh --overwrite
