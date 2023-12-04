
from typing import Optional
from engine.apps.phone_notifications.models import ProviderPhoneCall
from engine.apps.phone_notifications.phone_provider import ProviderFlags
from .phone_provider import PhoneProvider
from engine.apps.base.models import LiveSetting
from engine.apps.base.utils import live_settings
import requests
import json
import logging

logger = logging.getLogger(__name__)

class AsteriskPhoneProvider(PhoneProvider):
    """
    AsteriskPhoneProvider help send notification via Asterisk call center.
    It connect with Asterisk via ARI (Asterisk REST Interface).
    """

    def make_notification_call(self, number: str, text: str) -> Optional[ProviderPhoneCall]:
        call = ProviderPhoneCall(
            provider=self,
            number=number,
            text=text,
            status="pending"
        )
        # Save the call object to the database
        call.save()
        # Try to make the actual call using the make_call method
        try:
            self.make_call(number, text)
            # Update the call status to success
            call.status = "success"
        except Exception as e:
            # Update the call status to failed
            call.status = "failed"
            # Log the exception
            logger.exception("Failed to make notification call: ", e)
        # Save the updated call object to the database
        call.save()
        # Return the call object
        return call

    def make_call(self, number: str, text: str):
        # Prepare the request headers, parameters and payload
        rq_headers = {
            "Content-Type": "application/json"
        }

        rq_params = {
            "api_key": live_settings.ASTERISK_ARI_APIKEY,
            "callerId": live_settings.ASTERISK_ARI_CALLER_ID,
            "endpoint": f"PJSIP/{live_settings.ASTERISK_ARI_TRUNK_NAME}",
            "extension": live_settings.ASTERISK_ARI_EXTENSION,
            "context": live_settings.ASTERISK_ARI_CONTEXT
        }

        rq_payload = json.dumps({
            "variables": {
                "alertMessage": text
            }
        })

        logging.warning(rq_params)

        # Send a POST request to the Asterisk ARI endpoint to create a channel
        requests.post(
            live_settings.ASTERISK_ARI_ENDPOINT + '/channels',
            params=rq_params,
            headers=rq_headers,
            data=rq_payload
        )

    def make_verification_call(self, number: str):
        # Generate a random verification code
        code = self.generate_verification_code()
        # Create a verification message using the code
        message = f"Your verification code is {code}. Please enter it on the Grafana Oncall website."
        # Make a notification call using the message
        self.make_notification_call(number, message)
        # Return the code
        return code

    @property
    def flags(self) -> ProviderFlags:
        return ProviderFlags(
            configured=True,
            test_sms=False,
            test_call=True,
            verification_call=True,
            verification_sms=False,
        )