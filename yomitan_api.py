#!/usr/bin/env -S python3 -u

import datetime
import http.server
import json
import os
import signal
import struct
import sys
import time
import traceback
import urllib.parse
from typing import Any, Optional

ADDR = "127.0.0.1"
PORT = 19633
PROCESS_STARTUP_WAIT = 2

YOMITAN_API_NATIVE_MESSAGING_VERSION = 1
BLACKLISTED_PATHS = ["favicon.ico"]

script_path = os.path.realpath(os.path.dirname(__file__))
crowbarfile_path = os.path.join(script_path, ".crowbar")


def error_log(message: str, error: str = "") -> None:
    try:
        utc_time = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        with open(
            os.path.join(script_path, "error.log"), "a", encoding="utf8"
        ) as log_file:
            log_file.write(
                utc_time
                + ", "
                + str(message).replace("\r", r"\r").replace("\n", r"\n")
                + ", "
                + str(error).replace("\r", r"\r").replace("\n", r"\n")
                + "\n"
            )
    except Exception:
        pass


def ensure_single_instance() -> None:
    if os.path.exists(crowbarfile_path):
        try:
            with open(crowbarfile_path, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM if sys.platform != "win32" else 15)
            time.sleep(PROCESS_STARTUP_WAIT)
        except (OSError, ValueError, ProcessLookupError, PermissionError):
            pass

    try:
        with open(crowbarfile_path, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        error_log("Failed to write crowbar file", str(e))


def delete_crowbarfile() -> None:
    try:
        if os.path.exists(crowbarfile_path):
            os.remove(crowbarfile_path)
    except Exception:
        pass


def get_message() -> Optional[dict[str, Any]]:
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("@I", raw_length)[0]
    if message_length > 33554432:
        return None
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


def send_message(message_content: dict[str, Any]) -> None:
    encoded_content = json.dumps(message_content).encode("utf-8")
    encoded_length = struct.pack("@I", len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()


def send_response(
    request_handler: http.server.BaseHTTPRequestHandler,
    status_code: int,
    content_type: str,
    data: str,
) -> None:
    request_handler.send_response(status_code)
    request_handler.send_header("Content-type", content_type)
    request_handler.send_header("Access-Control-Allow-Origin", "*")
    request_handler.send_header("Access-Control-Allow-Methods", "*")
    request_handler.send_header("Access-Control-Allow-Headers", "*")
    request_handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    request_handler.end_headers()
    request_handler.wfile.write(bytes(data, "utf-8"))


def handle_invalid_method(request_handler: http.server.BaseHTTPRequestHandler) -> None:
    request_handler.send_error(
        405, str(request_handler.command) + " method not allowed"
    )
    request_handler.end_headers()


class RequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_POST(self) -> None:
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path[1:]
            params = urllib.parse.parse_qs(parsed_url.query)

            content_length_header = self.headers.get("Content-Length")
            content_length = int(content_length_header) if content_length_header else 0
            body = (
                self.rfile.read(content_length).decode("utf-8")
                if content_length > 0
                else "{}"
            )

            if path in BLACKLISTED_PATHS:
                send_response(self, 400, "", "")
                return

            if path in ["serverVersion", ""]:
                send_response(
                    self,
                    200,
                    "application/json",
                    json.dumps({"version": YOMITAN_API_NATIVE_MESSAGING_VERSION}),
                )
                return

            send_message({"action": path, "params": params, "body": body})
            yomitan_response = get_message()

            if yomitan_response and "responseStatusCode" in yomitan_response:
                send_response(
                    self,
                    yomitan_response["responseStatusCode"],
                    "application/json",
                    json.dumps(yomitan_response["data"], ensure_ascii=False),
                )
            else:
                send_response(
                    self,
                    500,
                    "application/json",
                    json.dumps({"error": "Communication error with extension"}),
                )
        except Exception:
            error_log(traceback.format_exc())
            send_response(
                self,
                500,
                "application/json",
                json.dumps({"error": "Internal API Error"}),
            )

    do_GET = handle_invalid_method
    do_HEAD = handle_invalid_method
    do_PUT = handle_invalid_method
    do_DELETE = handle_invalid_method
    do_CONNECT = handle_invalid_method
    do_OPTIONS = handle_invalid_method
    do_TRACE = handle_invalid_method
    do_PATCH = handle_invalid_method


if __name__ == "__main__":
    try:
        ensure_single_instance()
        http.server.HTTPServer.allow_reuse_address = True
        httpd = http.server.HTTPServer((ADDR, PORT), RequestHandler)
        httpd.serve_forever()
    except Exception:
        error_log(traceback.format_exc())
    finally:
        delete_crowbarfile()
