# SC-100 answer-key review

An independent review of this bank's answer keys against current Microsoft
documentation. The bank is a third-party exam dump: its keys are not
authoritative, and this file records which of them have actually been checked.

**Reviewed on:** 2026-09-07
**Objectives used:** [SC-100 study guide, skills measured as of July 28, 2026](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-100)

## Coverage

| | Count |
| --- | --- |
| Questions in the bank | 310 |
| Of those, scorable (have a gradeable key) | 222 |
| **Answer keys examined against Microsoft Learn** | **11** |
| — verified correct | 7 |
| — corrected | 3 |
| — flagged for manual review | 1 |
| **Not yet reviewed** | **299** |

> **Read this before trusting a key.** 11 of 310 keys have been checked. The
> remaining 299 are reproduced from the dump exactly as it had them and have
> **not** been independently verified. The simulator says so on every question:
> a reviewed item shows its verdict and a Microsoft Learn link with the answer,
> and an unreviewed item shows only what the source recorded.

## Also corrected

**Domain weightings.** The weighted practice exam drew questions on the wrong
proportions — 30–35% for security operations and 20–25% for infrastructure.
The current study guide gives 20–25 / 25–30 / 25–30 / 20–25, so the 50-question
draw changed from 11/17/11/11 to 11/14/14/11.

## Findings

| Question | Original answer | Final answer | Status | Confidence | Reason | Official source |
| --- | --- | --- | --- | --- | --- | --- |
| Standalone 20 | C. Microsoft Entra Private Access | B. Microsoft Entra Internet Access | CORRECTED | HIGH | Tenant restrictions are what stop a user signing in to any tenant other than your own, and in Global Secure Access they are delivered as Universal Tenant Restrictions on the Microsoft traffic profile — that is Microsoft Entra Internet Access. The Global… | [What is Global Secure Access? — feature comparison table](https://learn.microsoft.com/en-us/entra/global-secure-access/overview-what-is-global-secure-access) |
| Standalone 54 | B. Microsoft Defender foe App Service | B. Microsoft Defender foe App Service | VERIFIED | HIGH | Dangling DNS detection is a named capability of Microsoft Defender for App Service: it alerts when an App Service site is decommissioned and its custom domain (the CNAME) is left behind, which is exactly the subdomain-takeover risk the question describes.… | [Microsoft Defender for App Service — Dangling DNS detection](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-app-service-introduction) |
| Standalone 85 | A. From Azure Policy, assign a built-in policy definition that  | C. From Microsoft Defender for Cloud, turn on a security standa | CORRECTED | HIGH | Regulatory standards such as NIST SP 800-53 are turned on as security standards in Defender for Cloud — Regulatory compliance > Manage compliance policies > Security policies, then toggle the standard On. Only then does the subscription get assessed and… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 92 | D. B2B direct connect | D. B2B direct connect | VERIFIED | HIGH | B2B direct connect is the one feature built for Teams shared channels, and it satisfies every requirement in the stem: users collaborate with their home credentials so no guest object is created in contoso.com, inbound cross-tenant access settings can be… | [B2B direct connect overview](https://learn.microsoft.com/en-us/entra/external-id/b2b-direct-connect-overview) |
| Standalone 95 | A. Microsoft Entra Private Access for App1 and Microsoft Entra  | A. Microsoft Entra Private Access for App1 and Microsoft Entra  | VERIFIED | HIGH | This is the core Global Secure Access split. Microsoft Entra Private Access is the ZTNA service for private, corporate resources — the on-premises App1 — and replaces VPN with per-app access. Microsoft Entra Internet Access is the identity-aware secure web… | [What is Global Secure Access?](https://learn.microsoft.com/en-us/entra/global-secure-access/overview-what-is-global-secure-access) |
| Standalone 109 | A. Microsoft Entra Private Access | A. Microsoft Entra Private Access | VERIFIED | HIGH | An on-premises FTP server reached from the internet is a private resource on a non-HTTP protocol, and Private Access provides per-app access for TCP and UDP applications with Conditional Access applied per app — that is what makes it ZTNA rather than a… | [What is Global Secure Access? — Microsoft Entra Private Access](https://learn.microsoft.com/en-us/entra/global-secure-access/overview-what-is-global-secure-access) |
| Standalone 203 | D. From Defender for Cloud, add a regulatory compliance standar | D. From Defender for Cloud, add a regulatory compliance standar | VERIFIED | HIGH | Adding the regulatory compliance standard in Defender for Cloud is the first step: the standard has to be assigned to the scope before Defender for Cloud will assess the subscription against it or show anything on the regulatory compliance dashboard.… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 214 | A. Azure Active Directory Domain Services (Azure AD DS) | A. Azure Active Directory Domain Services (Azure AD DS) | VERIFIED | HIGH | Legacy applications issuing LDAP queries need a directory that speaks LDAP. Microsoft Entra Domain Services (formerly Azure AD DS) provides managed domain services — domain join, Group Policy, LDAP, and Kerberos/NTLM — without you deploying or patching… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |
| Standalone 215 | B. Microsoft Entra ID | C. Microsoft Entra Domain Services | CORRECTED | HIGH | This is word-for-word the same scenario as Standalone 214, which the source keys to Azure AD DS — so the source contradicts itself, and the Microsoft Entra ID key here is the wrong half of that contradiction. Microsoft Entra ID does not answer LDAP; it is… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |
| Standalone 217 | D. From Defender for Cloud, enable Defender for Cloud plans. | D. From Defender for Cloud, enable Defender for Cloud plans. | MANUAL_REVIEW | LOW | Flagged: the key is left as the source has it, but it looks wrong and the documentation does not settle the wording. This is the same NIST SP 800-53 scenario as Standalone 85 and 203, except the option 'add a regulatory compliance standard' is missing from… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 280 | B. Deploy Microsoft Entra Domain Services. | B. Deploy Microsoft Entra Domain Services. | VERIFIED | HIGH | An enterprise application that needs LDAP to look up attributes about Entra users needs a managed domain in front of Entra ID. Domain Services synchronises users, groups and credentials one way from Microsoft Entra ID and exposes them over LDAP and… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `VERIFIED` | The dump's key was checked against Microsoft documentation and is right. |
| `CORRECTED` | The dump's key was wrong. The bank grades the corrected answer, and the explanation opens with `THIS ANSWER WAS CORRECTED BY AI`. |
| `MANUAL_REVIEW` | Microsoft's documentation does not settle it. The key is left exactly as the dump had it, and the question is flagged in the simulator. |
| `AMBIGUOUS` | More than one answer is defensible as the question is worded. |
| `OUTDATED` | The item tests something that has since changed. |
| `NOT_REVIEWED` | Not yet examined. The default for every question absent from `build/review.json`. |

Confidence is `HIGH` when Microsoft documentation states the point explicitly,
`MEDIUM` when it is strongly supported but needs interpretation, and `LOW` when
the documentation is ambiguous or silent. A `LOW` finding is never allowed to
stand as `VERIFIED` or `CORRECTED` — the build refuses it.

## How to continue the review

Add an entry to `build/review.json` keyed `"<section>/<number>"`, then:

```bash
python build/bank.py && python build/assemble.py && python build/test_bank.py
```

`bank.py` refuses to build if an entry contradicts the question it names — a
wrong `originalAnswer`, a letter the question does not offer, a `LOW`-confidence
verdict presented as settled, or a `VERIFIED`/`CORRECTED` entry without a
`learn.microsoft.com` source. `test_bank.py` then checks that corrections
reached the published page and that the correction banner appears on corrected
questions and nowhere else.
