import json
import subprocess
import traceback
import urllib
from io import StringIO
import os
import urllib.request

from call_function_with_timeout import SetTimeoutDecorator

MASTER_URL = rf"https://raw.githubusercontent.com/INBGM0212-2023/exercises/main/week-04/P1042"


def get_exercise_id() -> str:
    return os.path.split(os.path.dirname(os.getcwd()))[-1]


def download_test_conf(exercise_id: str) -> dict[str, str]:
    with urllib.request.urlopen(rf"{MASTER_URL}/{exercise_id[:-2]}/test.json") as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_test_case(exercise_id: str, test_id: str) -> dict[str, str]:
    url = f"{MASTER_URL}/{exercise_id[:-2]}/{test_id}/test"
    with urllib.request.urlopen(f"{url}{exercise_id[-2:]}.in") as resp_in, urllib.request.urlopen(
            f"{url}.out") as resp_out:
        return {
            "in": resp_in.read().decode("utf-8"),
            "out": resp_out.read().decode("utf-8"),
        }


def download_unit_test_suite(exercise_id: str, test_id: str) -> dict[str, str]:
    with urllib.request.urlopen(f"{MASTER_URL}/{exercise_id[:-2]}/{test_id}/test.json") as resp:
        return json.loads(resp.read().decode("utf-8"))


def call(module: object) -> None:
    def exception_message(e: Exception) -> str:
        return f"""
                    
START ============================== UNIT TESTING {function_name}() ==============================

THE FOLLOWING EXCEPTION HAS BEEN THROWN:

{e}

END ================================ UNIT TESTING {function_name}() ==============================
"""

    conf = download_test_conf(get_exercise_id())
    for test_id in conf["tests"]:
        test_suite = download_unit_test_suite(get_exercise_id(), test_id)
        for function_name in test_suite:
            for test_case in test_suite[function_name]:
                try:
                    fun = getattr(module, function_name)
                except Exception as e:
                    raise AssertionError(exception_message(e)) from None
                results = SetTimeoutDecorator(test_case["limit"])(fun)(**test_case["in"])
                if results[1]:
                    raise AssertionError(exception_message(TimeoutError(f"Function <<{function_name}>> timed out after {test_case['limit']} seconds")))
                elif not results[0]:
                    raise AssertionError(exception_message(results[2]))
                if results[3] != test_case["out"]:
                    input_text = "\n".join([f"  {line}" for line in json.dumps(test_case['in'], indent=2).splitlines()])
                    raise AssertionError(f"""
                    
START ============================== UNIT TESTING {function_name}() ==============================

The expected and actual values differ!

ACTUAL PARAMETERS:

{input_text}

EXPECTED:

  <<{test_case['out']}>>

ACTUAL:

  <<{results[3]}>>

END ================================ UNIT TESTING {function_name}() ==============================
""")


def run() -> None:
    column_ids = ["in", "out", "act"]
    column_names = ["INPUT", "EXPECTED", "ACTUAL"]

    out = StringIO()
    conf = download_test_conf(get_exercise_id())
    for test_id in conf["tests"]:
        test_case = download_test_case(get_exercise_id(), test_id)
        process = subprocess.run(["python", "solution.py"], input=test_case["in"].encode("utf-8"),
                                 stdout=subprocess.PIPE, timeout=float(conf["timeout-cmd"]), universal_newlines=False)

        channels = {
            "in": [line.rstrip("\n") for line in test_case["in"].splitlines()],
            "out": [line.rstrip("\n") for line in test_case["out"].splitlines()],
            "act": [line.rstrip("\n") for line in process.stdout.decode("utf-8").splitlines()]
        }

        merged = []
        for i in range(max(len(channel) for channel in channels.values())):
            merged.append([
                channels[extension][i].replace(" ", "•") if i < len(channels[extension]) else ""
                for extension in column_ids
            ])

        width = [
            max(10, max(len(line) for line in channels[extension]) if channels[extension] else 0)
            for extension in column_ids
        ]

        if channels["act"] != channels["out"]:
            sep = {"sep": " | ", "file": out}
            end = {"end": " |\n"}

            print("START", "=" * 30, "RUN", test_id, "=" * 30, file=out)
            print(file=out)
            print(f"{' ':4}", *[f"{column_names[i].center(width[i])}" for i in range(len(column_names))], **sep, **end)
            print(f"{' ':4}", *['-' * w for w in width], **sep, **end)
            for i in range(len(merged)):
                print(f"{i:4}", *[f"{merged[i][n]:{width[n]}}" for n in range(len(column_names))],
                      " " if merged[i][1] == merged[i][2] else "<< !!!", **sep)

            print(file=out)
            print("END", "=" * 32, "RUN", test_id, "=" * 30, file=out)
            out.seek(0)
            out = "".join(out.readlines())
            raise AssertionError(f"""

The expected and actual outputs differ!

{out}
""")
