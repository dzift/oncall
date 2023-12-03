from typing import Optional
from engine.apps.phone_notifications.models import ProviderPhoneCall
from engine.apps.phone_notifications.phone_provider import ProviderFlags
from .phone_provider import PhoneProvider
from engine.apps.base.models import LiveSetting
from engine.apps.base.utils import live_settings


class AsteriskPhoneProvider(PhoneProvider):
    """
    AsteriskPhoneProvider help send notification via Asterisk call center.
    It connect with Asterisk via ARI (Asterisk REST Interface).
    """

    def make_notification_call(self, number: str, text: str) -> Optional[ProviderPhoneCall]:

        raise NotImplementedError

    def make_call(self, number: str, text: str):

        raise NotImplementedError

    def make_verification_call(self, number: str):

        raise NotImplementedError

    @property
    def flags(self) -> ProviderFlags:
        return ProviderFlags(
            configured=True,
            test_sms=False,
            test_call=True,
            verification_call=True,
            verification_sms=False,
        )
