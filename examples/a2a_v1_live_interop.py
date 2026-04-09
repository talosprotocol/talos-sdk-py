"""Live A2A v1 interoperability smoke against a running gateway."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from talos_sdk.a2a_v1 import A2AJsonRpcClient, A2AJsonRpcError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Talos A2A v1 live interop smoke")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8000", help="Gateway base URL")
    parser.add_argument("--api-token", default=None, help="Bearer token for the gateway")
    parser.add_argument("--prompt", default=None, help="Optional prompt to send via SendMessage")
    parser.add_argument(
        "--interop-profile",
        choices=("canonical", "upstream_v0_3", "upstream_java_hybrid"),
        default="canonical",
        help="Optional wire-compat profile for upstream interoperability runs",
    )
    parser.add_argument(
        "--exercise-streams",
        action="store_true",
        help="Also exercise SendStreamingMessage and SubscribeToTask against the target",
    )
    parser.add_argument(
        "--return-immediately",
        action="store_true",
        help="Set configuration.returnImmediately on send requests",
    )
    return parser.parse_args()


def pretty(title: str, payload: Any) -> None:
    print(f"\n== {title} ==")
    print(json.dumps(payload, indent=2, sort_keys=True))


def note(title: str, reason: str) -> None:
    pretty(title, {"skipped": True, "reason": reason})


def supports_authenticated_extended_card(card: Any) -> bool:
    return isinstance(card, dict) and bool(card.get("supportsAuthenticatedExtendedCard"))


def supports_extended_agent_card(card: Any) -> bool:
    capabilities = card.get("capabilities") if isinstance(card, dict) else None
    return isinstance(capabilities, dict) and bool(capabilities.get("extendedAgentCard"))


def task_id_from_send_result(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    task = payload.get("task")
    if isinstance(task, dict) and isinstance(task.get("id"), str):
        return task["id"]
    if payload.get("kind") == "task" and isinstance(payload.get("id"), str):
        return payload["id"]
    return None


def main() -> int:
    args = parse_args()
    client = A2AJsonRpcClient(
        args.gateway_url,
        api_token=args.api_token,
        interop_profile=args.interop_profile,
    )

    try:
        card = client.get_agent_card()
        pretty("Agent Card", card)
        if not supports_extended_agent_card(card):
            note(
                "Extended Agent Card",
                "Skipped because the target agent card does not advertise extended discovery",
            )
            note(
                "Authenticated Extended Agent Card",
                "Skipped because the target agent card does not advertise extended discovery",
            )
        elif args.interop_profile == "upstream_v0_3" and not supports_authenticated_extended_card(card):
            note(
                "Extended Agent Card",
                "Skipped because the target agent card does not advertise authenticated extended discovery",
            )
            note(
                "Authenticated Extended Agent Card",
                "Skipped because the target agent card does not advertise authenticated extended discovery",
            )
        else:
            pretty("Extended Agent Card", client.get_extended_agent_card())
            pretty("Authenticated Extended Agent Card", client.get_authenticated_extended_agent_card())
        if args.interop_profile == "upstream_v0_3":
            note("Task List", "Skipped for upstream_v0_3 because tasks/list is not guaranteed upstream")
        elif args.interop_profile == "upstream_java_hybrid":
            note(
                "Task List",
                "Skipped for upstream_java_hybrid because the official Java sample exposes a mixed task surface",
            )
        else:
            pretty("Task List", client.list_tasks(page_size=5))

        if args.prompt:
            send_result = client.send_message(
                args.prompt,
                configuration={"returnImmediately": args.return_immediately},
            )
            pretty("Send Message", send_result)
            task_id = task_id_from_send_result(send_result)
            if task_id is not None:
                try:
                    pretty("Get Task", client.get_task(task_id, include_artifacts=True))
                except A2AJsonRpcError as exc:
                    if args.interop_profile != "upstream_v0_3" or exc.code != -32601:
                        raise
                    note("Get Task", "Skipped for upstream_v0_3 because tasks/get is not implemented by the target")
            else:
                note("Get Task", "Skipped because SendMessage did not return a task id")
            if args.exercise_streams:
                pretty(
                    "Send Streaming Message",
                    list(
                        client.send_streaming_message(
                            args.prompt,
                            configuration={"returnImmediately": args.return_immediately},
                        )
                    ),
                )
                if task_id is None:
                    note("Subscribe To Task", "Skipped because SendMessage did not return a task id")
                else:
                    try:
                        pretty("Subscribe To Task", list(client.subscribe_to_task(task_id)))
                    except A2AJsonRpcError as exc:
                        if args.interop_profile != "upstream_v0_3" or exc.code != -32601:
                            raise
                        note(
                            "Subscribe To Task",
                            "Skipped for upstream_v0_3 because tasks/resubscribe is not implemented by the target",
                        )
    except A2AJsonRpcError as exc:
        print(
            json.dumps(
                {"error": {"code": exc.code, "message": str(exc), "data": exc.data}},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # pragma: no cover - CLI safeguard
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
