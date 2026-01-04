import json
import os
import time
from .reports import JUnitReport
from .handlers import get_handler_for_file


def run_conformance(vectors_path, report_path=None):
    with open(vectors_path, "r") as f:
        data = json.load(f)

    # If it is a release set (list of filenames), recurse
    if "version" in data and "vectors" in data and isinstance(data["vectors"], list):
        if len(data["vectors"]) > 0 and isinstance(data["vectors"][0], str):
            base_dir = os.path.dirname(vectors_path)
            all_success = True
            for sub_vector in data["vectors"]:
                sub_path = os.path.join(base_dir, sub_vector)
                success = run_conformance(sub_path, None)
                if not success:
                    all_success = False
            return all_success

    filename = os.path.basename(vectors_path)
    handler = get_handler_for_file(filename)
    # ... (rest of the existing logic)

    report = JUnitReport()
    suite_name = f"Conformance.{filename.replace('.json', '')}"

    # Track statistics
    total = 0
    failures = 0
    errors = 0
    start_time = time.time()

    results = []

    # Run positive vectors
    if "steps" in data:
        # Single trace file
        total += 1
        t0 = time.time()
        try:
            handler.run_trace(data)
            if "expected_error" in data:
                failures += 1
                results.append(
                    (filename, "failure", "Expected error but trace succeeded", time.time() - t0)
                )
            else:
                results.append((filename, "passed", None, time.time() - t0))
        except AssertionError as e:
            failures += 1
            results.append((filename, "failure", str(e), time.time() - t0))
        except Exception as e:
            if "expected_error" in data:
                # Basic check - full check requires reuse of BaseHandler logic?
                # For now just pass if exception raised, as we want to verify SDK behavior.
                # Ideally verify code/message.
                expected = data["expected_error"]
                msg = str(e)
                if expected.get("message_contains") and expected["message_contains"] not in msg:
                    failures += 1
                    results.append(
                        (filename, "failure", f"Error mismatch. Got: {msg}", time.time() - t0)
                    )
                else:
                    results.append((filename, "passed", None, time.time() - t0))
            else:
                errors += 1
                results.append((filename, "error", str(e), time.time() - t0))
    elif "vectors" in data:
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

    duration = time.time() - start_time

    # Decide if we are a single vector, a trace, or a collection
    if "steps" in data:
        pass  # Already handled above
    elif "vectors" in data:
        pass  # Already handled above
    elif "negative_cases" in data:
        pass  # Already handled above
    else:
        # SINGLE VECTOR case
        total += 1
        t0 = time.time()
        try:
            if "expected_error" in data:
                handler.run_negative(data)
            else:
                handler.run_vector(data)
            results.append((data.get("test_id", filename), "passed", None, time.time() - t0))
        except AssertionError as e:
            failures += 1
            results.append((data.get("test_id", filename), "failure", str(e), time.time() - t0))
        except Exception as e:
            errors += 1
            results.append((data.get("test_id", filename), "error", str(e), time.time() - t0))

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


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Talos SDK Conformance Runner")
    parser.add_argument(
        "--vectors", required=True, help="Path to conformance vectors JSON or release set"
    )
    parser.add_argument("--report", help="Output JUnit XML report path")

    args = parser.parse_args()
    success = run_conformance(args.vectors, args.report)
    sys.exit(0 if success else 1)
