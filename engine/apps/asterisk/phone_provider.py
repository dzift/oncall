import logging
from random import randint
from typing import Optional

import requests
import json
from django.core.cache import cache

from apps.base.utils import live_settings
from apps.phone_notifications.exceptions import FailedToMakeCall, FailedToStartVerification
from apps.phone_notifications.phone_provider import PhoneProvider, ProviderFlags
from apps.asterisk.models.phone_call import AsteriskCallStatuses, AsteriskPhoneCall

ASTERISK_CALL_URL = live_settings.ASTERISK_ARI_ENDPOINT

logger = logging.getLogger(__name__)


class AsteriskPhoneProvider(PhoneProvider):
    """
    AsteriskPhoneProvider help send notification via Asterisk call center.
    It connect with Asterisk via ARI (Asterisk REST Interface).
    """

    def make_notification_call(self, number: str, message: str) -> AsteriskPhoneCall:
        body = None

        try:
            response = self._connect_to_asterisk(number, message)

        except requests.exceptions.HTTPError:
            logger.exception(f"AsteriskPhoneProvider.make_notification_call: failed")
            raise FailedToMakeCall(graceful_msg=self._get_graceful_msg(body, number))
        except (requests.exceptions.ConnectionError, requests.exceptions.JSONDecodeError, TypeError):
            logger.exception(f"AsteriskPhoneProvider.make_notification_call: failed")
            raise FailedToMakeCall(graceful_msg=f"Failed make notification call to {number}")

        response.raise_for_status()
        body = response.json()
        if not body:
            logger.error("AsteriskPhoneProvider.make_notification_call: failed, empty body")
            raise FailedToMakeCall(graceful_msg=f"Failed make notification call to {number}, empty body")

        call_id = body.get("call_id")
        if not call_id:
            logger.error("AsteriskPhoneProvider.make_notification_call: failed, missing call id")
            raise FailedToMakeCall(graceful_msg=self._get_graceful_msg(body, number))

        logger.info(f"AsteriskPhoneProvider.make_notification_call: success, call_id {call_id}")

        return AsteriskPhoneCall(
            status=AsteriskCallStatuses.IN_PROCESS,
            call_id=call_id,
            caller_id=live_settings.ASTERISK_ARI_CALLER_ID,
        )

    def make_call(self, number: str, message: str):
        body = None

        try:
            response = self._connect_to_asterisk(number, message)
        except requests.exceptions.HTTPError:
            logger.exception(f"AsteriskPhoneProvider.make_call: failed")
            raise FailedToMakeCall(graceful_msg=self._get_graceful_msg(body, number))

        except (requests.exceptions.ConnectionError, requests.exceptions.JSONDecodeError, TypeError):
            logger.exception(f"AsteriskPhoneProvider.make_call: failed")
            raise FailedToMakeCall(graceful_msg=f"Failed make call to {number}")

        response.raise_for_status()
        body = response.json()
        if not body:
            logger.error("AsteriskPhoneProvider.make_call: failed, empty body")
            raise FailedToMakeCall(graceful_msg=f"Failed make call to {number}, empty body")

        call_id = body.get("call_id")
        if not call_id:
            raise FailedToMakeCall(graceful_msg=self._get_graceful_msg(body, number))

        logger.info(f"AsteriskPhoneProvider.make_call: success, call_id {call_id}")

    def _connect_to_asterisk(self, number: str, text: str, speaker: Optional[str] = None):
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "api_key": live_settings.ASTERISK_ARI_APIKEY,
            "callerId": live_settings.ASTERISK_ARI_CALLER_ID,
            "endpoint": f"PJSIP/{number}@{live_settings.ASTERISK_ARI_TRUNK_NAME}",
            "extension": live_settings.ASTERISK_ARI_EXTENSION,
            "context": live_settings.ASTERISK_ARI_CONTEXT
        }
        payload = json.dumps({
            "variables": {
                "alertMessage": text
            }
        })
        if speaker:
            params["speaker"] = speaker

        return requests.post(ASTERISK_CALL_URL + '/channels', headers=headers, params=params, data=payload)

    def _get_graceful_msg(self, body, number):
        if body:
            status = body.get("status")
            data = body.get("data")
            if status == "error" and data:
                return f"Failed make call to {number} with error: {data}"
        return f"Failed make call to {number}"

    def make_verification_call(self, number: str, codewspaces: str) -> AsteriskPhoneCall:
        body = None

        try:
            response = self._connect_to_asterisk(number, f"Your verification code is {codewspaces}")

        except requests.exceptions.HTTPError:
            logger.exception("AsteriskPhoneProvider.make_verification_call: failed")
            raise FailedToStartVerification(graceful_msg=self._get_graceful_msg(body, number))
        except (requests.exceptions.ConnectionError, requests.exceptions.JSONDecodeError, TypeError):
            logger.exception(f"AsteriskPhoneProvider.make_verification_call: failed")
            raise FailedToStartVerification(graceful_msg=f"Failed make verification call to {number}")

        response.raise_for_status()
        body = response.json()
        if not body:
            logger.error("AsteriskPhoneProvider.make_verification_call: failed, empty body")
            raise FailedToMakeCall(graceful_msg=f"Failed make verification call to {number}, empty body")

        call_id = body.get("call_id")
        if not call_id:
            raise FailedToStartVerification(graceful_msg=self._get_graceful_msg(body, number))

        return AsteriskPhoneCall(
            status=AsteriskCallStatuses.IN_PROCESS,
            call_id=call_id,
            caller_id=live_settings.ASTERISK_ARI_CALLER_ID,
        )

    def finish_verification(self, number, code):
        code_from_cache = cache.get(self._cache_key(number))
        return number if code_from_cache == code else None

    def _cache_key(self, number):
        return f"asterisk_provider_{number}"

    @property
    def flags(self) -> ProviderFlags:
        return ProviderFlags(
            configured=True,
            test_sms=False,
            test_call=True,
            verification_call=True,
            verification_sms=False,
        )
