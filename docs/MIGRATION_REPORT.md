# Intelligence Brain to ForgeMind AI migration

Migration completed: 15 August 2026

## Source and destination

- Source: preserved local `Industrial-Brain-AI-FINAL-DEPLOY` project
- Destination: separate `ForgeMind-AI-Azure-Conference` project
- The source project and live Render deployment were read only and remain unchanged.

The live web frontend was reachable, but its public `/api/*` endpoints returned HTTP 500 during migration. The preserved local SQLite database and its document directories were therefore used as the authoritative recoverable source.

## Migrated database records

| Table | Records |
|---|---:|
| Documents | 29 |
| Chunks | 969 |
| Entities | 552 |
| Entity relationships | 122 |
| Citations | 124 |
| Assets | 12 |
| Failures | 16 |
| Work orders | 5 |
| Inspections | 6 |
| Procedures | 2 |
| Regulations | 10 |
| Audit logs from source | 32 |

One additional audit entry records the ForgeMind migration.

## Files

- All 29 document records were relinked to files inside the separate ForgeMind project.
- No document was unresolved.
- The 52 compared source files were byte-identical to files already carried in ForgeMind.
- No filename/content conflict was found.
- The original SQLite database was copied to `backend/app/data/forgemind.db`.
- A portable JSON snapshot was created at `backend/app/data/legacy_snapshot.json`.
- The machine-readable manifest is `backend/migration/legacy_migration_manifest.json`.

## Important interpretation

Large dashboard figures such as 1,284 documents and 426 assets are presentation/demo figures in the frontend. They are not backed by exportable live API records. This migration reports only records verified in the preserved database and files.

## Re-run

```powershell
python backend/scripts/migrate_legacy_data.py `
  --source-root "C:\path\to\Industrial-Brain-AI-FINAL-DEPLOY" `
  --destination-root "."
```

The command refuses to overwrite an existing ForgeMind database unless `--force` is explicitly supplied.

Machine-specific Desktop paths are sanitized in the published migration manifest. Record counts, content hashes, completion time, and verification results are preserved.
