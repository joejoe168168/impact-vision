# Running Impact Vision for a team

On a laptop, Impact Vision runs as one local user and needs no sign-in. When a
fund team shares one server, turn on **OIDC sign-in**. Each person then works
in their fund's **tenant**, with a **role** that sets what they can do.

## 1. Register an app with your identity provider

Use Microsoft Entra ID, Google Workspace, Okta, Auth0 or Keycloak. Create a
web application (authorization-code flow; PKCE is always used) with this
redirect URL:

```
https://impact.yourfund.org/auth/callback
```

## 2. Configure and start

```bash
pip install "impact-vision[web,oidc]"
export IMPACT_VISION_OIDC_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
export IMPACT_VISION_OIDC_CLIENT_ID=<client id>
export IMPACT_VISION_OIDC_CLIENT_SECRET=<client secret>
export IMPACT_VISION_OIDC_ADMINS=head-of-impact@yourfund.org
export IMPACT_VISION_ALLOWED_HOSTS=impact.yourfund.org
impact-vision serve-web --host 0.0.0.0 --port 8788
```

Put it behind HTTPS (a reverse proxy such as Caddy or nginx), so the session
cookie is marked `Secure`.

| Setting | Default | Meaning |
|---|---|---|
| `IMPACT_VISION_OIDC_TENANT_CLAIM` | `tenant` | ID-token claim naming the tenant. Without it, the tenant is the email domain. |
| `IMPACT_VISION_OIDC_ROLES_CLAIM` | `roles` | Claim listing roles. |
| `IMPACT_VISION_OIDC_DEFAULT_ROLE` | `analyst` | Role used when the token names none. |
| `IMPACT_VISION_OIDC_ADMINS` | — | Emails that get `tenant_admin`. |
| `IMPACT_VISION_SESSION_SECRET` | generated file | Key that signs the 8-hour session cookie. Set it when running several workers. |
| `IMPACT_VISION_API_TENANT` | `default` | Tenant used for calls made with `IMPACT_VISION_API_KEY`. |

## Roles

| Role | Can |
|---|---|
| `viewer` | Read deals, theses and the portfolio |
| `analyst` | The viewer rights, plus run assessments, chat with the agent and generate reports |
| `ic_member` | The analyst rights, plus edit theses and the portfolio |
| `lp_relations` | The viewer rights, plus generate reports and create LP share links |
| `tenant_admin` | Everything, including the AI-provider settings and everyone's chats in the tenant |

## What a tenant isolates

- chat transcripts (each person sees their own; admins see the whole tenant);
- uploads and generated reports;
- the assessment and company-record database;
- the state store, which covers review queues, verification workspaces, LP Q&A, consents, the audit trail, webhooks and batch jobs.

Share links carry their tenant, so a recipient only ever sees that one report.

## MCP for remote agents

```bash
impact-vision mcp token create analyst-bot --scope assess --tenant yourfund.org
impact-vision serve-mcp --transport http --host 0.0.0.0 --allow-host impact.yourfund.org:443
```

The token is limited to its tenant and scopes, and every tool call is written to that tenant's audit trail.
