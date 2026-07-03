#!/usr/bin/env python3
"""nat_report.py - summarize network connections from a netstat-nat log or live capture."""

import subprocess
import sys


def usage(problem):
    """Print the problem and how to use the script, then exit with code 2."""
    print("error: " + problem, file=sys.stderr)
    print(
        """
usage: nat_report.py MODE [options]

modes (required, pick one):
  summary            total connections, counts by state and by client host
  top                busiest destination hosts

options:
  --file PATH        read connections from a netstat-nat log file
                     (default: capture live tcp connections with 'ss -tan')
  --proto NAME       only keep one protocol: tcp or udp
  --count NUMBER     how many destinations 'top' shows (default: 5)
  --report PATH      also save the output to a report file

exit codes: 0 = success, 1 = failure, 2 = incorrect usage
""",
        file=sys.stderr,
    )
    sys.exit(2)


def capture_live(lines):
    """Run 'ss -tan', append its output lines to 'lines', report success."""
    try:
        result = subprocess.run(["ss", "-tan"], capture_output=True, text=True)
    except OSError:
        return False
    if result.returncode != 0:
        return False
    # grabs the standard output and
    # saves each line from it into an
    # entry in a lines list
    lines.extend(result.stdout.splitlines())
    return True


def read_log(path, lines):
    """Read a log file, append its lines to 'lines', report success."""
    try:
        with open(path) as log:
            # saves each line as an entry in a list
            lines.extend(log.read().splitlines())
    except OSError:
        return False
    return True


def parse_connections(lines, wanted_proto):
    """Turn raw text lines into (proto, client, destination, state) tuples."""
    connections = []
    for line in lines:
        parts = line.split()
        # this parses the data lines
        # tcp  192.168.1.101:51834  142.250.72.14:https  ESTABLISHED
        # the header is never parsed
        if len(parts) >= 4 and parts[0] in ("tcp", "udp"):
            connection = (parts[0], parts[1], parts[2], parts[3])
        # this parses live 'ss -tan' lines
        # ESTAB  0  0  192.168.1.5:51234  93.184.216.34:443
        # state is first, addresses are fields 4 and 5,
        # and the protocol is always tcp because of the -t flag
        elif len(parts) >= 5 and parts[0].isupper() and ":" in parts[3]:
            connection = ("tcp", parts[3], parts[4], parts[0])
        else:
            continue
        # how the user wants to filter by protocol
        # udp, tcp, None (returns any protocol)
        if wanted_proto in (None, connection[0]):
            connections.append(connection)
    return connections


def host_part(address):
    """Return an address without its port, so '1.2.3.4:80' becomes '1.2.3.4'."""
    return address.rsplit(":", 1)[0]


def tally(items):
    """Count how many times each item appears."""
    counts = {}
    for item in items:
        # sets to 0 to initialize
        # otherwise adds 1 to counter
        # for the item
        counts[item] = counts.get(item, 0) + 1
    return counts


def format_counts(counts, limit):
    """Turn a counts dictionary into text lines, biggest first, at most 'limit'."""
    # receives a list like [("ESTABLISHED", 6), ("TIME_WAIT", 5), ...]
    # (it also processes counts for all the other types, like clients, destinations, etc.)
    # the "pair[1]" sorts the values by the second index of the tuple
    # the resulting ranked list keeps the same tuples just in a different
    # order within the list
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    if not ranked:
        return ["  (none)"]
    # this returns a string containing the tuples for each line
    # only prints out as many as defined by the limit
    return ["%6d  %s" % (number, name) for name, number in ranked[:limit]]


def summarize(connections, source):
    """Build the 'summary' mode report text."""
    states = tally(
        [connection[3] for connection in connections]
    )  # counts how many of CLOSE, ESTABLISHED, etc.
    clients = tally([host_part(connection[1]) for connection in connections])
    report_lines = [
        "Connection summary from " + source,
        "Total connections: " + str(len(connections)),
        "",
        "Connections by state:",
    ]
    report_lines.extend(format_counts(states, None))
    report_lines.append("")
    report_lines.append("Connections by client host:")
    report_lines.extend(format_counts(clients, None))
    return "\n".join(report_lines)


def top_destinations(connections, count, source):
    """Build the 'top' mode report text."""
    destinations = tally([host_part(connection[2]) for connection in connections])
    report_lines = ["Top %d destination hosts from %s" % (count, source), ""]
    report_lines.extend(format_counts(destinations, count))
    return "\n".join(report_lines)


def write_report(path, text):
    """Save the report text to a file, report success."""
    try:
        with open(path, "w") as report:
            report.write(text + "\n")
    except OSError:
        return False
    return True


def main():
    """Check arguments, gather connections, print the requested report."""
    arguments = sys.argv[1:]
    if not arguments:
        usage("missing mode")
    mode = arguments[0]
    if mode not in ("summary", "top"):
        usage("unknown mode: " + mode)

    # feeds in the option values from the args
    # using a dictionary.
    options = {"--file": None, "--proto": None, "--count": "5", "--report": None}
    position = 1
    while position < len(arguments):
        name = arguments[position]
        if name not in options:
            usage("unknown option: " + name)
        if position + 1 >= len(arguments):
            usage("option needs a value: " + name)
        options[name] = arguments[position + 1]
        position += 2

    # Checks proto and count option validity
    if options["--proto"] not in (None, "tcp", "udp"):  # should none be here??
        usage("--proto must be tcp or udp")  # None just isn't udp nor tcp
    if not options["--count"].isdigit() or int(options["--count"]) < 1:
        usage("--count must be a whole number above zero")

    # grabs the data from the logfile and/or captures live data
    lines = []  # the data is saved here. loaded is only used for error checking
    if options["--file"] is not None:
        source = options["--file"]
        # if statements don't create their own scope
        # loaded is main() scoped.
        loaded = read_log(source, lines)
    else:
        source = "live capture (ss -tan)"
        loaded = capture_live(lines)
    if not loaded:
        print("error: could not get connections from " + source, file=sys.stderr)
        sys.exit(1)

    connections = parse_connections(lines, options["--proto"])
    if mode == "summary":
        report = summarize(connections, source)
    else:
        report = top_destinations(connections, int(options["--count"]), source)
    print(report)

    if options["--report"] is not None:
        if not write_report(options["--report"], report):
            print("error: could not write " + options["--report"], file=sys.stderr)
            sys.exit(1)
        print("\nreport saved to " + options["--report"])

    sys.exit(0)


main()
