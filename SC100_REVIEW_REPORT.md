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
| **Answer keys examined against Microsoft Learn** | **23** |
| — verified correct | 14 |
| — corrected | 6 |
| — flagged for manual review | 3 |
| **Not yet reviewed** | **287** |

> **Read this before trusting a key.** 23 of 310 keys have been checked. The
> remaining 287 are reproduced from the dump exactly as it had them and have
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
| Standalone 24 | C. Microsoft Defender for Identity | C. Microsoft Defender for Identity | VERIFIED | HIGH | Defender for Identity is the only one of these that looks inside an on-premises AD DS domain. Its identity security posture assessments evaluate domain configuration and surface the weaknesses attackers exploit, which is exactly “identify configuration… | [Microsoft Defender for Identity overview](https://learn.microsoft.com/en-us/defender-for-identity/what-is) |
| Standalone 27 | A. Local Administrator Password Solution (LAPS) | A. Local Administrator Password Solution (LAPS) | VERIFIED | HIGH | Windows LAPS gives every machine a different, automatically rotated local administrator password. Microsoft lists the first benefit as “protection against pass-the-hash and lateral-traversal attacks”, which is the requirement word for word: if one… | [Windows LAPS overview](https://learn.microsoft.com/en-us/windows-server/identity/laps/laps-overview) |
| Standalone 36 | B. Configure Windows Local Administrator Password Solution (Win | A. Only add Group2 to the local Administrators group. | CORRECTED | MEDIUM | The question asks what to put in the local Administrators group of a privileged access device, and the keyed answer does not answer that question — configuring LAPS in an emulation mode sets how a password is stored, not who is a member of the group. It is… | [Windows LAPS overview](https://learn.microsoft.com/en-us/windows-server/identity/laps/laps-overview) |
| Standalone 54 | B. Microsoft Defender foe App Service | B. Microsoft Defender foe App Service | VERIFIED | HIGH | Dangling DNS detection is a named capability of Microsoft Defender for App Service: it alerts when an App Service site is decommissioned and its custom domain (the CNAME) is left behind, which is exactly the subdomain-takeover risk the question describes.… | [Microsoft Defender for App Service — Dangling DNS detection](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-app-service-introduction) |
| Standalone 85 | A. From Azure Policy, assign a built-in policy definition that  | C. From Microsoft Defender for Cloud, turn on a security standa | CORRECTED | HIGH | Regulatory standards such as NIST SP 800-53 are turned on as security standards in Defender for Cloud — Regulatory compliance > Manage compliance policies > Security policies, then toggle the standard On. Only then does the subscription get assessed and… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 87 | D. Azure AD Multi-Factor Authentication | D. Azure AD Multi-Factor Authentication | MANUAL_REVIEW | LOW | Flagged: the key looks wrong and the source seems to know it. The question asks what forces an upgrade from Microsoft Entra ID Free to Premium; the key says multifactor authentication, but the source’s own explanation links to the Privileged Identity… | — |
| Standalone 92 | D. B2B direct connect | D. B2B direct connect | VERIFIED | HIGH | B2B direct connect is the one feature built for Teams shared channels, and it satisfies every requirement in the stem: users collaborate with their home credentials so no guest object is created in contoso.com, inbound cross-tenant access settings can be… | [B2B direct connect overview](https://learn.microsoft.com/en-us/entra/external-id/b2b-direct-connect-overview) |
| Standalone 95 | A. Microsoft Entra Private Access for App1 and Microsoft Entra  | A. Microsoft Entra Private Access for App1 and Microsoft Entra  | VERIFIED | HIGH | This is the core Global Secure Access split. Microsoft Entra Private Access is the ZTNA service for private, corporate resources — the on-premises App1 — and replaces VPN with per-app access. Microsoft Entra Internet Access is the identity-aware secure web… | [What is Global Secure Access?](https://learn.microsoft.com/en-us/entra/global-secure-access/overview-what-is-global-secure-access) |
| Standalone 101 | D. Microsoft Defender for Identity | D. Microsoft Defender for Identity | VERIFIED | HIGH | Credential exposure in an AD DS domain is Defender for Identity's posture territory: it identifies risky configurations and exposures, analyses lateral movement paths showing how an attacker would traverse the environment, and surfaces the findings as… | [Microsoft Defender for Identity overview](https://learn.microsoft.com/en-us/defender-for-identity/what-is) |
| Standalone 109 | A. Microsoft Entra Private Access | A. Microsoft Entra Private Access | VERIFIED | HIGH | An on-premises FTP server reached from the internet is a private resource on a non-HTTP protocol, and Private Access provides per-app access for TCP and UDP applications with Conditional Access applied per app — that is what makes it ZTNA rather than a… | [What is Global Secure Access? — Microsoft Entra Private Access](https://learn.microsoft.com/en-us/entra/global-secure-access/overview-what-is-global-secure-access) |
| Standalone 119 | A. the Azure Monitor agent | A. the Azure Monitor agent | MANUAL_REVIEW | LOW | Flagged as a defective question rather than a wrong key. The stem asks which **two** solutions to include and says each correct answer is a complete solution, but the source records a single letter. Resource-based RBAC in Microsoft Sentinel is what… | — |
| Standalone 140 | C. inbound rules in network security groups (NSGs) | D. firewall rules for the storage account | CORRECTED | HIGH | A network security group cannot protect a storage account at all. NSGs filter traffic at a subnet or network interface inside a virtual network; a storage account is a PaaS service reached through its own public endpoint, which no NSG sits in front of. The… | [Azure Storage firewall rules and network access](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security) |
| Standalone 151 | A. Apply read-only locks on the storage accounts. | A. Apply read-only locks on the storage accounts. | VERIFIED | HIGH | The requirement that decides this is “minimize the impact on the legacy applications”. A read-only lock blocks the List Keys operation — Microsoft states plainly that “a read-only lock on a storage account prevents users from listing the account keys”,… | [Lock your Azure resources - considerations before applying locks](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/lock-resources) |
| Standalone 153 | B. Microsoft Defender for Identity | B. Microsoft Defender for Identity | VERIFIED | HIGH | Privilege escalation against a synced on-premises domain is a core Defender for Identity detection: it monitors “privilege escalation and suspicious role or group membership changes” and domain-dominance behaviour such as DCShadow and Golden Ticket. Note… | [Microsoft Defender for Identity overview](https://learn.microsoft.com/en-us/defender-for-identity/what-is) |
| Standalone 194 | A. Microsoft Intune Endpoint Privilege Management | A. Microsoft Intune Endpoint Privilege Management | VERIFIED | HIGH | Endpoint Privilege Management lets standard users run specific approved binaries elevated without ever joining the local Administrators group. The detail the question turns on is the elevation type: EPM normally elevates using an isolated virtual account,… | [Endpoint Privilege Management with Microsoft Intune](https://learn.microsoft.com/en-us/intune/intune-service/protect/epm-overview) |
| Standalone 203 | D. From Defender for Cloud, add a regulatory compliance standar | D. From Defender for Cloud, add a regulatory compliance standar | VERIFIED | HIGH | Adding the regulatory compliance standard in Defender for Cloud is the first step: the standard has to be assigned to the scope before Defender for Cloud will assess the subscription against it or show anything on the regulatory compliance dashboard.… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 214 | A. Azure Active Directory Domain Services (Azure AD DS) | A. Azure Active Directory Domain Services (Azure AD DS) | VERIFIED | HIGH | Legacy applications issuing LDAP queries need a directory that speaks LDAP. Microsoft Entra Domain Services (formerly Azure AD DS) provides managed domain services — domain join, Group Policy, LDAP, and Kerberos/NTLM — without you deploying or patching… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |
| Standalone 215 | B. Microsoft Entra ID | C. Microsoft Entra Domain Services | CORRECTED | HIGH | This is word-for-word the same scenario as Standalone 214, which the source keys to Azure AD DS — so the source contradicts itself, and the Microsoft Entra ID key here is the wrong half of that contradiction. Microsoft Entra ID does not answer LDAP; it is… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |
| Standalone 217 | D. From Defender for Cloud, enable Defender for Cloud plans. | D. From Defender for Cloud, enable Defender for Cloud plans. | MANUAL_REVIEW | LOW | Flagged: the key is left as the source has it, but it looks wrong and the documentation does not settle the wording. This is the same NIST SP 800-53 scenario as Standalone 85 and 203, except the option 'add a regulatory compliance standard' is missing from… | [Assign regulatory compliance standards in Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud/update-regulatory-compliance-packages) |
| Standalone 254 | D. Configure encryption by using customer-managed keys (CMKs) | A. Create shared access signatures (SAS). | CORRECTED | HIGH | The keyed answer confuses encryption with access control. Customer-managed keys change which key encrypts data at rest; they grant nobody access and expire for no one. A shared access signature is the delegated-access mechanism, and Microsoft describes it… | [Grant limited access to data with shared access signatures (SAS)](https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview) |
| Standalone 280 | B. Deploy Microsoft Entra Domain Services. | B. Deploy Microsoft Entra Domain Services. | VERIFIED | HIGH | An enterprise application that needs LDAP to look up attributes about Entra users needs a managed domain in front of Entra ID. Domain Services synchronises users, groups and credentials one way from Microsoft Entra ID and exposes them over LDAP and… | [Overview of Microsoft Entra Domain Services](https://learn.microsoft.com/en-us/entra/identity/domain-services/overview) |
| Standalone 289 | B. Endpoint Privilege Management (EPM) | B. Endpoint Privilege Management (EPM) | VERIFIED | HIGH | Installing an application needs administrative rights, and EPM grants exactly that for exactly that binary — elevation is scoped by rules to specific files, logged per elevation, and leaves the user a standard user the rest of the time. Microsoft frames it… | [Endpoint Privilege Management with Microsoft Intune](https://learn.microsoft.com/en-us/intune/intune-service/protect/epm-overview) |

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
