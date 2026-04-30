# Datovy model

## Hlavni princip

System je navrzeny kolem `Zakazky`.

- `E-mail` je vstup.
- `Zakazka` je hlavni kontejner prace.
- `Ukol`, `Faktura`, `Kalendarova udalost`, `Pripominka` a `Vykaz prace` se vazou k zakazce.
- `Pracovnik` nese sazby a odpovednost.

## Entity

### Zakazka (`projects`)
- `id`
- `name`
- `code`
- `status`
- `priority`
- `description`
- `customer_name`
- `contact_person`
- `contact_email`
- `contact_phone`
- `address`
- `planned_start_at`
- `planned_end_at`
- `actual_start_at`
- `actual_end_at`
- `budget_amount`
- `notes`
- `internal_notes`
- `created_at`

### E-mail (`emails`)
- `id`
- `thread_id`
- `sender`
- `subject`
- `body`
- `received_at`
- `category`
- `priority`
- `status`
- `attachments_json`
- `summary`
- `project_id`

### Ukol (`tasks`)
- `id`
- `title`
- `description`
- `priority`
- `status`
- `due_date`
- `source_email_id`
- `project_id`
- `assigned_worker_id`
- `estimated_hours`
- `completed_at`
- `created_at`

### Faktura (`invoices`)
- `id`
- `supplier`
- `invoice_number`
- `amount`
- `currency`
- `due_date`
- `status`
- `source_email_id`
- `attachment_path`
- `project_id`
- `created_at`

### Kalendarova udalost (`calendar_events`)
- `id`
- `title`
- `starts_at`
- `ends_at`
- `description`
- `location`
- `status`
- `source_email_id`
- `project_id`
- `assigned_worker_id`
- `created_at`

### Pracovnik (`workers`)
- `id`
- `full_name`
- `role`
- `email`
- `phone`
- `hourly_rate`
- `payout_rate`
- `status`
- `created_at`

### Vykaz prace (`work_logs`)
- `id`
- `project_id`
- `worker_id`
- `work_date`
- `hours`
- `notes`
- `starts_at`
- `ends_at`
- `travel_km`
- `material_cost`
- `payout_amount`
- `billable_amount`
- `created_at`

## Vztahy

- `emails.project_id -> projects.id`
- `tasks.project_id -> projects.id`
- `tasks.assigned_worker_id -> workers.id`
- `invoices.project_id -> projects.id`
- `calendar_events.project_id -> projects.id`
- `calendar_events.assigned_worker_id -> workers.id`
- `work_logs.project_id -> projects.id`
- `work_logs.worker_id -> workers.id`

## Financni logika

Zakazka pocita orientacni financni prehled z techto vstupu:

- `invoice_total`: soucet faktur navazanych na zakazku
- `payout_total`: soucet vyplat z vykazu prace
- `material_total`: soucet materialovych nakladu z vykazu prace
- `balance`: `invoice_total - payout_total - material_total`

## Viceplatformni smer

Datovy model je pripraveny pro:

- desktop klient
- web klient
- mobilni klient nad API
- sdileny kalendar a dalsi integrace
