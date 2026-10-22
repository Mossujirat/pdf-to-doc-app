# Public entry through its own Tailscale Funnel node, not Cloudflare

The Chatbot project on the same server is reached through a Cloudflare Tunnel, and this service was meant to follow it. We did not, because Cloudflare decrypts traffic at its edge: every uploaded file, often a confidential contract, would pass through Cloudflare in readable form, against the promise that files go only to our server. Tailscale Funnel ends TLS on our own machine, and its relay cannot read the traffic. The service gets its own Tailscale node and name (`pdf.<tailnet>.ts.net`), run as a container in its own compose project, rather than a port on gmt's existing name. Browsers send a host's cookies to every port on it, so Chatbot's login cookie would reach this service, and Funnel's only other ports, 8443 and 10000, are often blocked.

## Consequences

- The address is a `ts.net` name, not our own domain.
- There is no Cloudflare WAF in front. Bots are held back by Turnstile, which works on hostnames outside Cloudflare, and by per-IP limits.
- The client IP comes from the `X-Forwarded-For` header that Funnel and Serve set to the client's own address, replacing any the client sent (tailscale v1.102.5). Staging showed that a forged one changes nothing.
- The nodes live in the operator's own tailnet, `tail46a117.ts.net`, into which `gmt` is shared from Chatbot's. The two services share no tailnet.
- The node is tagged in the tailnet policy, allowed to use Funnel, and allowed to reach no other device.
- Funnel has bandwidth limits that Tailscale does not publish.
