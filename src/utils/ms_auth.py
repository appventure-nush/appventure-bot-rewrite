import uuid
from typing import Any, MutableMapping

import msal

from config import config

from werkzeug.datastructures import MultiDict

application = msal.ConfidentialClientApplication(
    client_id=config.ms_auth_client_id,
    authority=f"https://login.microsoftonline.com/{config.ms_auth_tenant_id}",
    client_credential=config.ms_auth_secret,
)

auth_flows: MutableMapping[str, Any] = {}


def get_ms_auth_link():
    state_nonce = uuid.uuid4()

    auth_flow = application.initiate_auth_code_flow(
        scopes=["User.Read"], redirect_uri=f"{config.ms_auth_redirect_domain}", state=state_nonce
    )

    auth_flows[str(state_nonce)] = auth_flow

    return auth_flow["auth_uri"]


def on_ms_auth_response(args: MultiDict[str, str]) -> bool:
    auth_flow = auth_flows.get(args.get('state', ''), None)
    if not auth_flow:
        return False

    return True

__all__ = ["get_ms_auth_link", "on_ms_auth_response"]
