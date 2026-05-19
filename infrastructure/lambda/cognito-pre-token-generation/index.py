"""
Cognito Pre-Token Generation Lambda trigger (V1_0).

Runs before Cognito issues an ID token. Reads custom:roles from the user's
profile attributes (written there by the IdP attribute mapping) and injects
it into the ID token claims so the backend JWT validator can read IdP roles.

Trigger version: V1_0 — uses claimsOverrideDetails / claimsToAddOrOverride.
Wired via CDK lambdaTriggers.preTokenGeneration which registers V1_0.

Design rules:
  - NEVER raise an exception. A Lambda crash here causes Cognito to return
    400 from /oauth2/token and breaks login for every user. The try/except
    at the outermost level ensures that even unexpected errors return the
    unmodified event so the login succeeds without the injected claim.
  - Log enough to diagnose problems without logging PII (no token values).
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context) -> dict:
    """Pre-Token Generation V1_0 trigger handler.

    AWS calls this with a trigger event structured as:
    {
      "triggerSource": "TokenGeneration_Authentication" | ...,
      "request": {
        "userAttributes": { "sub": "...", "email": "...", "custom:roles": "...", ... },
        "groupConfiguration": { "groupsToOverride": [...], ... }
      },
      "response": {}
    }

    V1_0 response shape:
    {
      "response": {
        "claimsOverrideDetails": {
          "claimsToAddOrOverride": { "<claim>": "<value>", ... },
          "claimsToSuppress": [ "<claim>", ... ]
        }
      }
    }
    """
    try:
        trigger_source = event.get("triggerSource", "unknown")
        user_attributes = event.get("request", {}).get("userAttributes", {})

        logger.info("Pre-token trigger source: %s", trigger_source)

        custom_roles_raw = user_attributes.get("custom:roles", "")

        if custom_roles_raw:
            logger.info(
                "Injecting custom:roles into ID token (%d chars)",
                len(custom_roles_raw),
            )
            event.setdefault("response", {})
            event["response"]["claimsOverrideDetails"] = {
                "claimsToAddOrOverride": {
                    "custom:roles": custom_roles_raw,
                }
            }
        else:
            logger.info("No custom:roles on user profile — skipping injection")

    except Exception:
        # Safety net: log the error but return the unmodified event so the
        # user's login still succeeds. Missing the claim is better than a
        # broken auth flow.
        logger.exception(
            "Unexpected error in pre-token generation trigger — returning unmodified event"
        )

    return event
