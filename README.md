# Local Assistant

Zakladni kostra AI asistenta pro e-maily, ukoly, kalendar, faktury a pripominky.

## Rezimy behu

CLI klient:

```bash
python run.py
```

Desktop GUI:

```bash
python run_gui.py
```

Web API:

```bash
python run_web.py
```

Background worker jen jednou:

```bash
python run_worker.py --once
```

Background worker periodicky:

```bash
python run_worker.py
```

Po spusteni `run_web.py`:

- webove rozhrani bezi na `http://127.0.0.1:8000`
- API bezi na `http://127.0.0.1:8000`
- interaktivni dokumentace je na `http://127.0.0.1:8000/docs`

## Viceplatformni smer

- desktop GUI zustava jako lokalni klient
- web API je nova hlavni viceplatformni vrstva pro notebook, telefon a dalsi klienty
- konkretni domenu a vazby popisuje [docs/data_model.md](docs/data_model.md)

## OpenAI triage

Pro AI navrhy nad e-maily nastav v `.env`:

```bash
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=low
```

Kdyz `OPENAI_API_KEY` neni vyplneny, aplikace automaticky pouzije stavajici rule-based fallback.

## Gmail OAuth setup

1. V Google Cloud vytvor Desktop OAuth client a stahni `credentials.json` do korene projektu.
2. Nainstaluj zavislosti:

```bash
pip install -r requirements.txt
```

3. Vytvor lokalni token:

```bash
python scripts/gmail_oauth_setup.py
```

4. Potom spust worker:

```bash
python run_worker.py --once
```

## Seed dat

```bash
python scripts/seed_data.py
```

## Testy

```bash
python -m unittest
```
