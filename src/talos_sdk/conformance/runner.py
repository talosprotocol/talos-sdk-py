import json
import os
import time
from .reports import JUnitReport
from .handlers import get_handler_for_file


def run_conformance(vectors_path, report_path=None):
    with open(vectors_path, "r") as f:
        data = json.load(f)

    filename = os.path.basename(vectors_path)
    handler = get_handler_for_file(filename)

    if not handler:
        print(f"No handler found for {filename}")
        return False

    report = JUnitReport()
    suite_name = f"Conformance.{filename.replace('.json', '')}"

    # Track statistics
    total = 0
    failures = 0
    errors = 0
    start_time = time.time()

    results = []

    # Run positive vectors
    if "vectors" in data:
        for vec in data["vectors"]:
            total += 1
            t0 = time.time()
            try:
                handler.run_vector(vec)
                results.append((vec["test_id"], "passed", None, time.time() - t0))
            except AssertionError as e:
                failures += 1
                results.append((vec["test_id"], "failure", str(e), time.time() - t0))
            except Exception as e:
                errors += 1
                results.append((vec["test_id"], "error", str(e), time.time() - t0))

    # Run negative cases
    if "negative_cases" in data:
        for vec in data["negative_cases"]:
            total += 1
            t0 = time.time()
            try:
                handler.run_negative(vec)
                results.append((vec["test_id"], "passed", None, time.time() - t0))
            except AssertionError as e:
                failures += 1
                results.append((vec["test_id"], "failure", str(e), time.time() - t0))
            except Exception as e:
                errors += 1
                results.append((vec["test_id"], "error", str(e), time.time() - t0))

    duration = time.time() - start_time

    # Generate report
    if report_path:
        suite = report.add_testsuite(suite_name, total, failures, errors, duration)
        for test_id, status, message, duration in results:
            case = report.add_testcase(suite, test_id, suite_name, duration)
            if status == "failure":
                report.add_failure(case, message)
            elif status == "error":
                report.add_error(case, message)

        report.write(report_path)
        print(f"Report written to {report_path}")

    # Output to stdout
    print(f"Ran {total} tests in {duration:.4f}s")
    if failures > 0 or errors > 0:
        print(f"FAILED (failures={failures}, errors={errors})")

        print("\nFailures:")
        for test_id, status, message, _ in results:
            if status in ("failure", "error"):
                print(f"[{status.upper()}] {test_id}: {message}")

        return False
    else:
        print("OK")
        return True
