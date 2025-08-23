# Truhlik Controller

Small FastAPI backend + static UI to control relays and execute time-based schedules.

## API (relevant)
- `POST /check_schedule` — evaluates the schedule and sets relays accordingly.

## Cron (run schedule check every minute)
Add the following line to your crontab (e.g., `crontab -e`) to call the scheduler once per minute:

```
* * * * * /usr/bin/curl -fsS -m 10 -X POST http://truhlik.local:8080/check_schedule -o /dev/null
```

Notes:
- `-f` fail on HTTP errors, `-sS` silent but still prints errors, `-m 10` sets a 10s timeout, `-o /dev/null` discards output.
- Adjust the base URL if your server is not `http://truhlik.local:8080`.
- If you prefer using an environment variable:

```
* * * * * BE_PATH=http://truhlik.local:8080 /usr/bin/curl -fsS -m 10 -X POST "$BE_PATH/check_schedule" -o /dev/null
```

Alternatively, you can implement a systemd timer for more robust scheduling.