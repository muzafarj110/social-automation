# Email delivery (Resend) — why verification / reset emails aren't arriving

## The cause
The app's `RESEND_FROM` defaults to **`onboarding@resend.dev`** — Resend's shared
**test sender**. It will only deliver to **your own Resend account email**. Every other
recipient (new signups, password resets to other addresses) is **rejected with 403**,
so the email never arrives. That's why a reset to your own inbox worked, but new
signups don't get verified.

## The fix — verify a domain in Resend (one time)
1. Resend dashboard → **Domains → Add domain** (e.g. `yourdomain.com` or a subdomain
   like `mail.yourdomain.com`).
2. Add the **DNS records Resend shows** (SPF + DKIM, and DMARC if offered) at your
   domain registrar. Wait for Resend to show **Verified** (minutes to a couple hours).
3. In Railway → app service → **Variables**, set:
   | Variable | Value |
   |---|---|
   | `RESEND_FROM` | `Autopilot <noreply@yourdomain.com>` (an address on the verified domain) |
   | `RESEND_API_KEY` | your Resend API key (confirm it's still set) |
   | `APP_BASE_URL` | `https://social-automation-production-209c.up.railway.app` (powers the links) |
4. Redeploy. Now verification + reset emails reach **any** recipient.

## Until the domain is verified
- The app no longer **locks people out**: if `RESEND_API_KEY` is unset, new signups are
  auto-verified (so you can still use the app). With a key set but using the test sender,
  non-owner signups stay unverified — that's expected until the domain is live.
- Every verification/reset link is also **written to the server logs** (Railway → app →
  Logs), e.g. `Email verification for x@y.com (sent=False): https://…/#verify?token=…`.
  You can copy that link to verify/reset manually while testing, even if the email didn't send.

## Quick test after the fix
Sign up with a real external address → the verification email should arrive from your
domain → click it → you're verified and logged in. Then try Forgot password to the same
address.
