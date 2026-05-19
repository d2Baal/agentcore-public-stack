"""
Cognito Pre-Token Generation Lambda trigger.

Runs before Cognito issues an ID token. Reads custom:roles from the user's
profile attributes (written there by the IdP attribute mapping) and injects
it into the token claims so the backend JWT validator can read IdP roles.

This is the recommended approach for surfacing custom attributes in tokens
without changing App Client readAttributes (which can break OAuth flows).

Trigger version: 2_0 (supports both V1 and V2 token customisation events).
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context) -> dict:
    """Pre-Token Generation trigger handler.

    AWS calls this with a trigger event structured as:
    {
      "triggerSource": "TokenGeneration_Authentication" | ...,
      "request": {
        "userAttributes": { "sub": "...", "email": "...", "custom:roles": "...", ... },
        "groupConfiguration": { "groupsToOverride": [...], ... }
      },
      "response": {}
    }

    We add custom:roles to claimsToAddOrOverride so it appears in the ID token
    regardless of what the App Client's readAttributes allow.
    """
    trigger_source = event.get("triggerSource", "")
    user_attributes = event.get("request", {}).get("userAttributes", {})

    logger.info(f"Pre-token trigger: {trigger_source}")

    custom_roles_raw = user_attributes.get("custom:roles", "")

    if custom_roles_raw:
        logger.info(f"Injecting custom:roles into token: {custom_roles_raw}")
        event.setdefault("response", {})
        event["response"]["claimsAndScopeOverrideDetails"] = {
            "idTokenGeneration": {
                "claimsToAddOrOverride": {
                    "custom:roles": custom_roles_raw,
                }
            }
        }
    else:
        logger.info("No custom:roles found on user profile — skipping injection")

    return event
