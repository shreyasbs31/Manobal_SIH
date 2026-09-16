# Saathi Trusted Web Activity

Package id `in.gov.mha.manobal.saathi`. Build with Bubblewrap from this folder after the web app is reachable.

```
npx @bubblewrap/cli init --manifest=http://localhost:3000/manifest.webmanifest
npx @bubblewrap/cli build
```

Digital Asset Links must list the signing fingerprint on `/.well-known/assetlinks.json` or Android treats the TWA as an untrusted Custom Tab.

## PIN fallback (spec 30.1)

Passkeys are the default sign-in. If the device has no passkey, the login screen still offers the demo role doors plus a six-digit PIN field stored only on the device. The PIN never leaves the phone. Push and the offline cache use the same origin as the PWA.

## Real-phone check

This workspace cannot reach a physical Android handset. Until a device is available, treat passkey, push, and airplane-mode cache as 31.1: verified in the Playwright PWA path and documented here, not ticked as a live-device result.
