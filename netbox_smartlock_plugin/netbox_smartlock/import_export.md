# SmartLock Import/Export Contract

SmartLock CSV import and CSV export share the field list defined in
`netbox_smartlock.contracts.SMARTLOCK_IMPORT_FIELDS`.

Required fields:

- `name`
- `code`
- `asset_group`
- `status`
- `device_type`

Reference fields:

- `asset_group`, `region`, `site`, and `location` use slugs.
- `id` updates an existing SmartLock during round-trip import.
- `rack_lookup` supports `rack`, `site|rack`, or `site|location|rack`.
- When `rack_lookup` is provided, SmartLock derives `site`, `location`, and `region` from the Rack where possible.

Export modes:

- Core NetBox table CSV export remains the CSV export path and uses the SmartLock import contract above.
- SmartLock Excel is an additional reporting format and includes derived fields such as `rack_lookup`, `warranty_state`, and `uploaded_files`.
