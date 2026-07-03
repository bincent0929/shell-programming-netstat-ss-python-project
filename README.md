# nat_report.py

## Project description

`nat_report.py` is a command-line utility that analyzes network connections and
reports derived metrics about them: totals, counts by connection state, counts
by client host, and the top-N busiest destination hosts.

It can read connections from two sources:

1. A saved `netstat-nat` log file (via `--file`), such as the output collected
   from a NAT gateway with `netstat-nat -n > nat-to-clients.log`.
2. A live capture of the local machine's TCP connections, gathered by running
   the standard `ss -tan` command through `subprocess` (the default when no
   `--file` is given). Capturing live socket information is not built into
   Python, so a command-line tool is used for it; all parsing, counting, and
   sorting is done in Python because those capabilities are built in.

## Supported modes and options

```
usage: nat_report.py MODE [options]
```

### Modes (required, pick one)

| Mode      | What it does                                                     |
|-----------|------------------------------------------------------------------|
| `summary` | Total connections, counts by state, counts by client host        |
| `top`     | Busiest destination hosts, most connections first                |

### Options (all optional)

| Option           | What it does                                                        |
|------------------|---------------------------------------------------------------------|
| `--file PATH`    | Read connections from a netstat-nat log instead of a live capture   |
| `--proto NAME`   | Only keep one protocol: `tcp` or `udp`                              |
| `--count NUMBER` | How many destinations `top` shows (default: 5)                      |
| `--report PATH`  | Also save the printed output to a report file                       |

## Exit code meanings

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| 0    | Pass / success                                                 |
| 1    | Fail (log file unreadable, live capture failed, report not written) |
| 2    | Incorrect usage (bad mode, unknown option, bad option value)   |

## How to test locally

No privileged access is needed. From the project directory:

```sh
# Summary of the included sample log
python3 nat_report.py summary --file sample-netstat-nat.log

# Top 3 destination hosts, TCP only, saved to a report file
python3 nat_report.py top --file sample-netstat-nat.log --count 3 --proto tcp --report report.txt

# Live capture of this machine's TCP connections (uses ss -tan)
python3 nat_report.py summary

# Check the exit codes
python3 nat_report.py summary --file sample-netstat-nat.log; echo "exit: $?"   # 0
python3 nat_report.py summary --file no-such-file.log;       echo "exit: $?"   # 1
python3 nat_report.py bogus-mode;                            echo "exit: $?"   # 2
python3 nat_report.py;                                       echo "exit: $?"   # 2 (prints usage)
```
