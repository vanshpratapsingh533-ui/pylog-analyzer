import codecs
import datetime
from collections import Counter
from pathlib import Path


MAX_TOP = 100
# Only this many example errors are kept for each response code (and for
# unreadable lines). The totals are still counted for every line.
ERRORS_KEPT_PER_CODE = 1000
CHUNK_SIZE = 1024 * 1024

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}
MONTH_NUMS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def sort_key_for_time(bucket: str) -> str:
    try:
        if "-W" in bucket:
            return bucket
        parts = bucket.split("/")
        if len(parts) == 3:
            day = parts[0]
            mon = MONTH_MAP.get(parts[1], parts[1])
            rest = parts[2]
            return f"{rest[:4]}-{mon}-{day:0>2}{rest[4:]}"
        elif len(parts) == 2:
            mon = MONTH_MAP.get(parts[0], parts[0])
            year = parts[1]
            return f"{year}-{mon}"
        return bucket
    except Exception:
        return bucket


STATUS_CODES = {
    100: ("Continue", "The server told the visitor to go ahead and send the rest of its request."),
    101: ("Switching Protocols", "The visitor asked to change how they talk to the server, and the server agreed."),
    102: ("Processing", "The server received the request and is still working on it."),
    103: ("Early Hints", "The server sent a first hint about what the page needs while it prepares the full answer."),
    200: ("OK", "The request worked and the visitor got what they asked for."),
    201: ("Created", "The request worked and something new was created, such as an account or a file."),
    202: ("Accepted", "The server took the request but has not finished working on it yet."),
    203: ("Non-Authoritative Information", "The request worked, but the answer was changed on the way by another server."),
    204: ("No Content", "The request worked and there was nothing to send back."),
    205: ("Reset Content", "The request worked and the visitor should clear the form they were filling in."),
    206: ("Partial Content", "The server sent only part of the file, which is normal for video and large downloads."),
    207: ("Multi-Status", "The server sent back several results at once, one for each part of the request."),
    208: ("Already Reported", "The server already listed this item earlier in the same answer."),
    226: ("IM Used", "The server answered with the changes to a file instead of the whole file."),
    300: ("Multiple Choices", "There is more than one place the visitor could be sent."),
    301: ("Moved Permanently", "The page has a new address for good. Visitors are sent there."),
    302: ("Found", "The page is temporarily at another address. Visitors are sent there."),
    303: ("See Other", "The visitor is sent to a different page to see the result of their request."),
    304: ("Not Modified", "The page has not changed since the visitor last saw it, so their saved copy was used."),
    305: ("Use Proxy", "The visitor was told to go through a proxy server. This is rarely used now."),
    307: ("Temporary Redirect", "The page is temporarily somewhere else, and the visitor should repeat the same kind of request there."),
    308: ("Permanent Redirect", "The page has moved for good, and the visitor should repeat the same kind of request there."),
    400: ("Bad Request", "The request was not put together correctly. Check what the visitor or app is sending."),
    401: ("Unauthorized", "The visitor was not logged in or used the wrong details. Check the login steps."),
    402: ("Payment Required", "Payment is needed to see this. It is rarely used, so check how your site uses it."),
    403: ("Forbidden", "The visitor is not allowed in. Check who has access and who owns the files."),
    404: ("Not Found", "The page was not found. Fix the link or put the missing page back."),
    405: ("Method Not Allowed", "This page does not accept that kind of request. Check which request types it allows."),
    406: ("Not Acceptable", "The server cannot send the page in a form the visitor can accept. Check the language or file type settings."),
    407: ("Proxy Authentication Required", "The visitor has to log in to a proxy server first. Check the proxy settings."),
    408: ("Request Timeout", "The visitor took too long. Check for slow connections and how busy the server is."),
    409: ("Conflict", "The request clashes with the current state of the item, such as two people editing it at once."),
    410: ("Gone", "The page was removed on purpose and will not come back. Remove links that still point to it."),
    411: ("Length Required", "The request did not say how big it was. Check what the visitor or app is sending."),
    412: ("Precondition Failed", "A condition set by the visitor was not met. Check the headers the app is sending."),
    413: ("Content Too Large", "The visitor sent more data than the server accepts. Check the upload size limits."),
    414: ("URI Too Long", "The web address was too long for the server. Check for links that stack up too many details."),
    415: ("Unsupported Media Type", "The server does not accept that kind of file or data. Check what the app is uploading."),
    416: ("Range Not Satisfiable", "The visitor asked for a part of a file that does not exist. Check partial download requests."),
    417: ("Expectation Failed", "The server could not meet what the visitor asked for before sending. Check the request headers."),
    418: ("I'm a Teapot", "A joke code that some sites use on purpose. It is usually safe to ignore, unless you did not set it up."),
    421: ("Misdirected Request", "The request was sent to a server that cannot answer it. Check how your sites share an address."),
    422: ("Unprocessable Content", "The server understood the request but the details in it were not valid. Check the data being sent."),
    423: ("Locked", "The item is locked and cannot be changed right now."),
    424: ("Failed Dependency", "The request failed because another step it relied on failed first."),
    425: ("Too Early", "The server will not act on a request that might be sent again. Check for repeated requests."),
    426: ("Upgrade Required", "The visitor needs to switch to a newer way of connecting. Check the connection settings."),
    428: ("Precondition Required", "The server wants the visitor to include a condition with the request. Check what the app is sending."),
    429: ("Too Many Requests", "Someone sent too many requests. Consider limiting how often a visitor can ask."),
    431: ("Request Header Fields Too Large", "The visitor sent too much information in the header of the request. Check for oversized cookies."),
    451: ("Unavailable For Legal Reasons", "The page is blocked for legal reasons. Check whether a legal order applies."),
    499: ("Client Closed Request", "The visitor gave up and left before the server answered. This is a nginx code, and it often means the page is slow."),
    500: ("Internal Server Error", "Something broke on the server. Look in the app and server logs for the cause."),
    501: ("Not Implemented", "The server does not support what was asked. Check that the feature or request type is set up."),
    502: ("Bad Gateway", "One server got a bad reply from another. Check the service behind it and the connection."),
    503: ("Service Unavailable", "The server could not take the request. Check if it is overloaded, being worked on, or waiting on something else."),
    504: ("Gateway Timeout", "A server behind this one took too long. Check how slow it is and how long you wait for it."),
    505: ("HTTP Version Not Supported", "The server does not support the version of the web protocol the visitor used. Check the server settings."),
    506: ("Variant Also Negotiates", "The server is set up in a way that makes it loop. Check its content settings."),
    507: ("Insufficient Storage", "The server has run out of space. Free up disk space."),
    508: ("Loop Detected", "The server got stuck in a loop while handling the request. Check the settings for circular links."),
    510: ("Not Extended", "The server needs more details to carry out the request. Check the extensions it expects."),
    511: ("Network Authentication Required", "The visitor must log in to the network first, as at a public Wi-Fi page."),
    520: ("Unknown Error (Cloudflare)", "Cloudflare got an unexpected answer from your server. Check your server logs."),
    521: ("Web Server Is Down (Cloudflare)", "Cloudflare could not reach your server. Check that it is running and not blocking Cloudflare."),
    522: ("Connection Timed Out (Cloudflare)", "Cloudflare waited too long to connect to your server. Check how busy the server is."),
    523: ("Origin Is Unreachable (Cloudflare)", "Cloudflare could not find a route to your server. Check the address and DNS settings."),
    524: ("A Timeout Occurred (Cloudflare)", "Your server connected but took too long to answer. Check for slow pages."),
}


GROUP_NAMES = {
    1: ("Informational", "The server sent a progress note. Nothing is wrong."),
    2: ("Success", "The request worked."),
    3: ("Redirect", "The visitor was sent to another address."),
    4: ("Client Error", "The request had a problem. Check the link, the login, and the permissions."),
    5: ("Server Error", "Something went wrong on the server. Check the logs and make sure everything it depends on is running."),
}


def explain_status(code: int) -> tuple[str, str]:
    if code in STATUS_CODES:
        return STATUS_CODES[code]
    if code // 100 in GROUP_NAMES:
        return GROUP_NAMES[code // 100]
    if code != 0:
        return "Unknown Code", "This is not a standard response code. Check what your server or app is sending."
    return "Unreadable Line", "This line does not look like a normal log line. Check how your server writes its logs."


def parse_line(raw_line: str) -> dict:
    line = raw_line.strip()
    if not line:
        raise ValueError("Empty line")

    first_token_end = line.find(" ")
    if first_token_end == -1:
        raise ValueError("Missing IP address")
    ip = line[:first_token_end]

    open_bracket = line.find("[")
    close_bracket = line.find("]")
    if open_bracket == -1 or close_bracket == -1 or close_bracket < open_bracket:
        raise ValueError("Missing or malformed timestamp")
    timestamp = line[open_bracket + 1:close_bracket]

    quote_start = line.find('"', close_bracket)
    if quote_start == -1:
        raise ValueError("Missing request section")
    quote_end = line.find('"', quote_start + 1)
    if quote_end == -1:
        raise ValueError("Unterminated request section")

    request_text = line[quote_start + 1:quote_end]
    request_parts = request_text.split()
    if len(request_parts) < 2:
        raise ValueError("Request section is incomplete")
    method, path = request_parts[0], request_parts[1]
    if not method.isalpha() or not method.isupper():
        raise ValueError("Invalid HTTP method")

    remainder = line[quote_end + 1:].strip().split()
    if not remainder:
        raise ValueError("Missing status code")
    if not remainder[0].isdigit() or len(remainder[0]) != 3:
        raise ValueError("Status code must be 3 digits")
    status = int(remainder[0])
    size = remainder[1] if len(remainder) > 1 else "-"

    day_str = timestamp[:2]
    mon_str = timestamp[3:6]
    year_str = timestamp[7:11]
    try:
        d = int(day_str)
        m = MONTH_NUMS.get(mon_str, 1)
        y = int(year_str)
        wk = datetime.date(y, m, d).isocalendar()[1]
        week_str = f"{y}-W{wk:02d}"
    except Exception:
        week_str = f"{year_str}-W01"

    return {
        "ip": ip,
        "timestamp": timestamp,
        "second": timestamp[:20],
        "minute": timestamp[:17],
        "hour": timestamp[:14],
        "day": timestamp[:11],
        "week": week_str,
        "month": f"{mon_str}/{year_str}",
        "method": method,
        "path": path,
        "status": status,
        "size": size,
        "raw": line,
    }


class LogAnalyzer:
    def __init__(self, top_limit: int = MAX_TOP, suspicious_ratio: float = 0.05, suspicious_min_hits: int = 100):
        self.top_limit = top_limit
        self.suspicious_ratio = suspicious_ratio
        self.suspicious_min_hits = suspicious_min_hits
        self.total_lines = 0
        self.malformed_lines = 0
        self.status_counter = Counter()
        self.ip_counter = Counter()
        self.path_counter = Counter()
        self.method_counter = Counter()
        self.error_log = []
        self.error_kept = Counter()
        self.line_number = 0
        self.second_counter = Counter()
        self.minute_counter = Counter()
        self.hour_counter = Counter()
        self.day_counter = Counter()
        self.week_counter = Counter()
        self.month_counter = Counter()
        self.error_hour_counter = Counter()

    def record_malformed(self, line_number: int, raw_line: str) -> None:
        self.malformed_lines += 1
        if self.error_kept["Malformed"] >= ERRORS_KEPT_PER_CODE:
            return
        self.error_kept["Malformed"] += 1
        label, suggestion = explain_status(0)
        self.error_log.append({
            "lineNumber": line_number,
            "status": "Malformed",
            "description": label,
            "suggestion": suggestion,
            "raw": raw_line.strip(),
        })

    def record_valid_line(self, line_number: int, entry: dict) -> None:
        self.status_counter[entry["status"]] += 1
        self.ip_counter[entry["ip"]] += 1
        self.path_counter[entry["path"]] += 1
        self.method_counter[entry["method"]] += 1
        self.second_counter[entry["second"]] += 1
        self.minute_counter[entry["minute"]] += 1
        self.hour_counter[entry["hour"]] += 1
        self.day_counter[entry["day"]] += 1
        self.week_counter[entry["week"]] += 1
        self.month_counter[entry["month"]] += 1

        if 400 <= entry["status"] <= 599:
            self.error_hour_counter[entry["hour"]] += 1
            if self.error_kept[entry["status"]] >= ERRORS_KEPT_PER_CODE:
                return
            self.error_kept[entry["status"]] += 1
            label, suggestion = explain_status(entry["status"])
            self.error_log.append({
                "lineNumber": line_number,
                "status": entry["status"],
                "description": label,
                "suggestion": suggestion,
                "ip": entry["ip"],
                "path": entry["path"],
                "method": entry["method"],
                "timestamp": entry["timestamp"],
                "raw": entry["raw"],
            })

    def feed_lines(self, lines) -> None:
        for raw_line in lines:
            self.line_number += 1
            if not raw_line.strip():
                continue
            self.total_lines += 1
            try:
                entry = parse_line(raw_line)
            except ValueError:
                self.record_malformed(self.line_number, raw_line)
                continue
            self.record_valid_line(self.line_number, entry)

    def feed(self, log_text: str) -> None:
        self.feed_lines(log_text.splitlines())

    def feed_stream(self, stream, length: int) -> None:
        """Read the log in small pieces so a big file never sits in memory all at once."""
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        leftover = ""
        remaining = length
        while remaining > 0:
            chunk = stream.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            text = leftover + decoder.decode(chunk)
            lines = text.split("\n")
            leftover = lines.pop()
            self.feed_lines(lines)
        leftover += decoder.decode(b"", final=True)
        if leftover:
            self.feed_lines([leftover])

    def top(self, counter: Counter) -> list[dict]:
        return [{"label": str(key), "count": count}
                for key, count in counter.most_common(self.top_limit)]

    def find_suspicious_ips(self) -> list[dict]:
        threshold = max(self.suspicious_min_hits, self.total_lines * self.suspicious_ratio)
        return [{"ip": ip, "requests": count}
                for ip, count in self.ip_counter.most_common()
                if count >= threshold]

    def find_error_spikes(self) -> list[dict]:
        if not self.hour_counter or not self.total_lines:
            return []
        total_errors = sum(c for code, c in self.status_counter.items() if 400 <= code <= 599)
        overall_rate = total_errors / self.total_lines
        spikes = []
        for hour, total in self.hour_counter.items():
            errors = self.error_hour_counter.get(hour, 0)
            if errors < 10:
                continue
            hour_rate = errors / total
            if overall_rate > 0 and hour_rate >= 2 * overall_rate:
                spikes.append({
                    "hour": hour,
                    "requests": total,
                    "errors": errors,
                    "errorRate": round(hour_rate * 100, 1),
                })
        return sorted(spikes, key=lambda x: x["errorRate"], reverse=True)

    def report(self, file_name: str = "server.log") -> dict:
        http_errors = sum(count for code, count in self.status_counter.items() if 400 <= code <= 599)
        total_bad = http_errors + self.malformed_lines
        error_rate = round((total_bad / self.total_lines) * 100, 2) if self.total_lines else 0.0

        return {
            "fileName": file_name,
            "summary": {
                "totalLines": self.total_lines,
                "malformedCount": self.malformed_lines,
                "httpErrors": http_errors,
                "errorRate": error_rate,
                "uniqueIps": len(self.ip_counter),
            },
            "topIps": self.top(self.ip_counter),
            "topPaths": self.top(self.path_counter),
            "topMethods": self.top(self.method_counter),
            "statusCodes": [{"label": str(code), "name": explain_status(code)[0],
                             "info": explain_status(code)[1], "count": count}
                            for code, count in self.status_counter.most_common()],
            "errors": self.error_log,
            "errorsTotal": total_bad,
            "errorsKeptPerCode": ERRORS_KEPT_PER_CODE,
            "errorsTrimmed": len(self.error_log) < total_bad,
            "suspiciousIps": self.find_suspicious_ips(),
            "requestsOverTime": {
                "second": sorted(
                    [{"label": k, "count": c} for k, c in self.second_counter.most_common(500)],
                    key=lambda x: sort_key_for_time(x["label"]),
                ),
                "minute": sorted(
                    [{"label": k, "count": c} for k, c in self.minute_counter.items()],
                    key=lambda x: sort_key_for_time(x["label"]),
                ),
                "hour": sorted(
                    [{"label": k, "count": c} for k, c in self.hour_counter.items()],
                    key=lambda x: sort_key_for_time(x["label"]),
                ),
                "day": sorted(
                    [{"label": k, "count": c} for k, c in self.day_counter.items()],
                    key=lambda x: sort_key_for_time(x["label"]),
                ),
                "week": sorted(
                    [{"label": k, "count": c} for k, c in self.week_counter.items()],
                    key=lambda x: x["label"],
                ),
                "month": sorted(
                    [{"label": k, "count": c} for k, c in self.month_counter.items()],
                    key=lambda x: sort_key_for_time(x["label"]),
                ),
            },
            "errorSpikes": self.find_error_spikes(),
        }


def analyse_log(log_text: str, file_name: str = "server.log", top_limit: int = MAX_TOP) -> dict:
    analyzer = LogAnalyzer(top_limit=top_limit)
    analyzer.feed(log_text)
    return analyzer.report(file_name)


def analyse_stream(stream, length: int, file_name: str = "server.log", top_limit: int = MAX_TOP) -> dict:
    analyzer = LogAnalyzer(top_limit=top_limit)
    analyzer.feed_stream(stream, length)
    return analyzer.report(file_name)
