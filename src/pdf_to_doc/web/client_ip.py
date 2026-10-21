"""Whose daily allowance a request counts against: its client's address.

The address comes from the header the trusted proxy (Tailscale's container) sets, and only on
requests from that proxy; any other request counts against its connection's own address. No
other header is read, whatever a visitor sends. An IPv6 address counts as its /64 block, which
one home or phone is usually given whole, so that changing address within it gains nothing.
"""

import ipaddress
from dataclasses import dataclass
from typing import Self

from fastapi import Request

from pdf_to_doc.web.settings import Misconfigured, Settings


@dataclass(frozen=True)
class ClientIp:
    trusted_proxy: str | None
    header: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """The rule the settings ask for. The public service refuses to start without the proxy
        and its header, as every visitor would otherwise share the proxy's one allowance."""
        if settings.production and not (settings.trusted_proxy and settings.client_ip_header):
            raise Misconfigured("the public service needs the trusted proxy and the header it sets")
        return cls(settings.trusted_proxy, settings.client_ip_header)

    def of(self, request: Request) -> str:
        """The client's address, or its IPv6 /64 block, as the allowance counts it."""
        peer = request.client.host if request.client else ""
        if self.trusted_proxy and self.header and peer == self.trusted_proxy:
            # The proxy adds the address it saw last: on a line of its own, or after any the visitor sent.
            lines = request.headers.getlist(self.header)
            said = lines[-1].rsplit(",", 1)[-1].strip() if lines else ""
            if (address := _address(said)) is not None:
                return address
        return _address(peer) or peer


def _address(text: str) -> str | None:
    """The address `text` holds, written one way, with IPv6 as its /64 block; or None."""
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:  # an IPv4 address carried in IPv6
            return str(address.ipv4_mapped)
        return str(ipaddress.IPv6Network((address, 64), strict=False))
    return str(address)
