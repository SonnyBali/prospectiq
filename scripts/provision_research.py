"""Inspect dedicated research infrastructure; mutate only with owner-authorized --apply.

Uses official Google Auth + Cloud Tasks Python SDK. IAM uses authenticated official
REST APIs, preserving etags, conditional bindings and unrelated grants. Never
enqueues tasks, invokes models, reads secrets, deploys, or contacts prospects.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Callable

import google.auth
from google.api_core.exceptions import AlreadyExists, GoogleAPICallError, NotFound
from google.auth.transport.requests import AuthorizedSession
from google.cloud import tasks_v2
from google.iam.v1 import policy_pb2
from google.protobuf.json_format import MessageToDict, ParseDict

PROJECT = "ai-leadscore"
REGION = "us-central1"
QUEUE = "prospectiq-research"
SERVICE = "prospectiq"
RUNTIME = f"prospectiq-runtime@{PROJECT}.iam.gserviceaccount.com"
DISPATCH = f"prospectiq-research-dispatch@{PROJECT}.iam.gserviceaccount.com"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
# Queue/IAM RPCs reject deadlines above 30 seconds. Leave clock/transport
# headroom rather than putting the SDK deadline exactly at that ceiling.
TASKS_RPC_TIMEOUT = 20


class ProvisionError(RuntimeError):
    """Only sanitized diagnostics may leave this helper."""


def request_json(session, method, url, *, label, missing_ok=False, **kwargs):
    response = session.request(method, url, timeout=30, **kwargs)
    if missing_ok and response.status_code == 404:
        return None
    if not response.ok:
        raise ProvisionError(f"{label}: HTTP {response.status_code}; provider body omitted")
    return response.json()


def has_grant(policy, role, member):
    return any(
        item.get("role") == role and not item.get("condition") and member in item.get("members", [])
        for item in policy.get("bindings", [])
    )


def add_grant(policy, role, member):
    """Merge exactly one unconditional grant without weakening conditional grants."""
    result = copy.deepcopy(policy)
    if has_grant(result, role, member):
        return result
    for binding in result.setdefault("bindings", []):
        if binding.get("role") == role and not binding.get("condition"):
            binding.setdefault("members", []).append(member)
            return result
    result["bindings"].append({"role": role, "members": [member]})
    return result


def ensure_grant(read: Callable, write: Callable, role, member, resource, apply, reports):
    policy = read()
    present = has_grant(policy, role, member)
    if not present and apply:
        write(add_grant(policy, role, member))
        if not has_grant(read(), role, member):
            raise ProvisionError(f"{resource}: IAM readback did not confirm requested grant")
    reports.append({"resource": resource, "role": role, "member": member,
                    "status": "existing" if present else "applied_verified" if apply else "planned"})


def rest_policy(session, base, *, project=False, service_account=False, missing=False):
    def read():
        # Resource Manager and IAM service accounts use POST; Cloud Run uses GET.
        use_post = project or service_account
        kwargs = ({"json": {"options": {"requestedPolicyVersion": 3}}} if use_post
                  else {"params": {"options.requestedPolicyVersion": 3}})
        return request_json(session, "POST" if use_post else "GET", base + ":getIamPolicy",
                            label="iam_read", missing_ok=missing, **kwargs) or {}

    def write(policy):
        request_json(session, "POST", base + ":setIamPolicy", label="iam_write",
                     json={"policy": policy})

    return read, write


def provision(apply=False):
    credentials, _ = google.auth.default(scopes=SCOPES)
    client = tasks_v2.CloudTasksClient(credentials=credentials)
    queue_name = client.queue_path(PROJECT, REGION, QUEUE)
    reports = []
    with AuthorizedSession(credentials) as session:
        project_base = f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT}"
        project = request_json(session, "GET", project_base, label="project_read")
        project_number = project.get("projectNumber")
        if not project_number or project.get("projectId") != PROJECT:
            raise ProvisionError("project_read: unexpected project identity")
        for api in ("cloudtasks.googleapis.com", "aiplatform.googleapis.com", "iam.googleapis.com", "run.googleapis.com"):
            state = request_json(session, "GET",
                                 f"https://serviceusage.googleapis.com/v1/projects/{project_number}/services/{api}",
                                 label="api_read")
            reports.append({"api": api, "state": state.get("state")})
            if state.get("state") != "ENABLED":
                raise ProvisionError(f"{api}: API must be enabled separately before provisioning")
        iam_base = f"https://iam.googleapis.com/v1/projects/{PROJECT}/serviceAccounts"
        runtime_state = request_json(session, "GET", f"{iam_base}/{RUNTIME}", label="runtime_read")
        if runtime_state.get("disabled"):
            raise ProvisionError("runtime_read: dedicated runtime account is disabled")
        run_base = f"https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/services/{SERVICE}"
        request_json(session, "GET", run_base, label="run_read")
        dispatch_state = request_json(session, "GET", f"{iam_base}/{DISPATCH}",
                                      label="dispatch_read", missing_ok=True)
        if dispatch_state and dispatch_state.get("disabled"):
            raise ProvisionError("dispatch_read: dedicated dispatch account is disabled")
        if dispatch_state is None and apply:
            request_json(session, "POST", iam_base, label="dispatch_create",
                         json={"accountId": "prospectiq-research-dispatch",
                               "serviceAccount": {"displayName": "ProspectIQ research task dispatch"}})
            request_json(session, "GET", f"{iam_base}/{DISPATCH}", label="dispatch_readback")
        reports.append({"service_account": DISPATCH,
                        "status": "existing" if dispatch_state else "created_verified" if apply else "planned"})
        try:
            queue = client.get_queue(name=queue_name, timeout=TASKS_RPC_TIMEOUT)
            queue_present = True
        except NotFound:
            queue, queue_present = None, False
        if not queue_present and apply:
            try:
                client.create_queue(parent=client.common_location_path(PROJECT, REGION), queue={
                    "name": queue_name,
                    "rate_limits": {"max_dispatches_per_second": 1, "max_concurrent_dispatches": 1},
                    "retry_config": {"max_attempts": 3, "min_backoff": {"seconds": 10},
                                     "max_backoff": {"seconds": 300}, "max_retry_duration": {"seconds": 3600}},
                }, timeout=TASKS_RPC_TIMEOUT)
            except AlreadyExists:
                pass
            queue = client.get_queue(name=queue_name, timeout=TASKS_RPC_TIMEOUT)
        reports.append({"queue": queue_name,
                        "status": "existing_preserved" if queue_present else "created_verified" if apply else "planned",
                        "state": queue.state.name if queue is not None else "MISSING"})

        def queue_policy_read():
            if not queue_present and not apply:
                return {}
            policy = client.get_iam_policy(request={"resource": queue_name,
                                                   "options": {"requested_policy_version": 3}}, timeout=TASKS_RPC_TIMEOUT)
            return MessageToDict(policy)

        def queue_policy_write(policy):
            client.set_iam_policy(request={"resource": queue_name,
                                           "policy": ParseDict(policy, policy_pb2.Policy())}, timeout=TASKS_RPC_TIMEOUT)

        runtime_member, dispatch_member = f"serviceAccount:{RUNTIME}", f"serviceAccount:{DISPATCH}"
        agent_member = f"serviceAccount:service-{project_number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
        ensure_grant(queue_policy_read, queue_policy_write, "roles/cloudtasks.enqueuer", runtime_member,
                     queue_name, apply, reports)
        dispatch_policy = rest_policy(session, f"{iam_base}/{DISPATCH}", service_account=True,
                                      missing=not apply and not dispatch_state)
        ensure_grant(*dispatch_policy, "roles/iam.serviceAccountUser", runtime_member, DISPATCH, apply, reports)
        # Current official HTTP-task guide also requires the primary Tasks agent to actAs this identity.
        ensure_grant(*dispatch_policy, "roles/iam.serviceAccountUser", agent_member, DISPATCH, apply, reports)
        ensure_grant(*rest_policy(session, run_base), "roles/run.invoker", dispatch_member,
                     f"CloudRun/{SERVICE}", apply, reports)
        project_policy = rest_policy(session, project_base, project=True)
        ensure_grant(*project_policy, "roles/aiplatform.user", runtime_member, PROJECT, apply, reports)
        # The normal Tasks service-agent role already grants getOpenIdToken; avoid redundant TokenCreator.
        agent_has_tokens = has_grant(project_policy[0](), "roles/cloudtasks.serviceAgent", agent_member)
        if not agent_has_tokens:
            ensure_grant(*dispatch_policy, "roles/iam.serviceAccountTokenCreator", agent_member,
                         DISPATCH, apply, reports)
        else:
            reports.append({"resource": DISPATCH, "role": "roles/iam.serviceAccountTokenCreator",
                            "member": agent_member, "status": "unneeded_existing_tasks_service_agent_role"})
    return {"project": PROJECT, "mode": "apply" if apply else "read_only_plan", "resources": reports,
            "tasks_enqueued": 0, "models_invoked": 0, "secrets_read": 0,
            "queue_running": bool(queue is not None and queue.state == tasks_v2.Queue.State.RUNNING),
            "iam_bindings_verified": bool(apply),
            "integration_tested": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply scoped changes only after owner authorization")
    args = parser.parse_args()
    try:
        print(json.dumps(provision(args.apply)))
    except ProvisionError as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 1
    except (GoogleAPICallError, google.auth.exceptions.GoogleAuthError) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__, "diagnostics": "omitted"}))
        return 1
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__, "diagnostics": "omitted"}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
