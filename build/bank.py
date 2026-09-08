"""Turn the parsed dump into the bank the simulator ships.

Numbering follows the source: each section counts from 1, so an item is
identified by its section and its number there, and `n` is an internal id used
only for ordering and saved state.

Three shapes come out:
  choice - stem, lettered options, answer key. Graded.
  match  - drop-downs with a correct value per box. Graded all-or-nothing.
           Only where the real choice lists are known; the dump records these
           as pictures, so most answer areas cannot become one.
  info   - no gradeable question. The dump's answer for these is a graphic, so
           the graphic is shown on reveal rather than an invented key.
"""
import json, os, re
from collections import Counter

import paths
import review as review_mod

parsed = json.load(open(paths.PARSED, encoding='utf-8'))
imgmap = json.load(open(paths.IMGMAP, encoding='utf-8'))

CASE_META = {'cs1': {'n': 1, 'name': 'Fabrikam, Inc.'},
             'cs2': {'n': 2, 'name': 'Litware, Inc.'}}

# Answer areas whose real choice lists are known from outside the dump, which
# is the only way one can be graded — the dump itself draws them as pictures.
ANSWER_AREAS = {
    ('std', 2): [
        {'label': 'To automate vulnerability code scanning',
         'value': 'GitHub Enterprise Cloud',
         'options': ['GitHub Enterprise Cloud', 'GitHub Enterprise Server', 'GitHub Team']},
        {'label': 'To automatically generate pull requests',
         'value': 'Dependabot',
         'options': ['Dependabot', 'Codespaces', 'Dependency Tracker']}
    ],
    ('std', 3): [
        {'label': 'For NIST',
         'value': 'Microsoft Defender for Cloud',
         'options': ['Microsoft Defender for Cloud',
                     'Microsoft Defender Vulnerability Management',
                     'Microsoft Sentinel']},
        {'label': 'For GDPR',
         'value': 'Microsoft Purview Compliance Manager',
         'options': ['Microsoft Priva',
                     'Microsoft Purview Communication Compliance',
                     'Microsoft Purview Compliance Manager']}
    ],
    ('std', 11): [
        {'label': 'For the containers',
         'value': 'Blob',
         'options': ['Account', 'Blob', 'Container']},
        {'label': 'For the shares',
         'value': 'Share',
         'options': ['Account', 'File', 'Share']}
    ],
    ('std', 21): [
        {'label': 'Role to assign to the Fabrikam helpdesk users for contoso.com',
         'value': 'Password Administrator',
         'options': ['Directory Readers', 'Helpdesk Administrator', 'Password Administrator']},
        {'label': 'To restrict the scope of the role assignments for the Fabrikam helpdesk users, use',
         'value': 'A custom role',
         'options': ['A custom role', 'An access package', 'An administrative unit']},
        {'label': 'Role to assign to the Fabrikam helpdesk users to reset the Contoso user passwords',
         'value': 'Password Administrator',
         'options': ['Directory Readers', 'Helpdesk Administrator', 'Password Administrator']}
    ],
    ('std', 28): [
        {'label': "For the database administrators",
         'value': "Always Encrypted",
         'options': ["Always Encrypted", "Dynamic data masking", "Row-level security (RLS)", "Transparent Data Encryption (TDE)"]},
        {'label': "For the operators",
         'value': "Dynamic data masking",
         'options': ["Always Encrypted", "Dynamic data masking", "Row-level security (RLS)", "Transparent Data Encryption (TDE)"]}
    ],
    ('std', 30): [
        {'label': "Ensures that the fabrikam.com users can be granted permissions to the Teams channels in contoso.com",
         'value': "Microsoft Entra B2B collaboration",
         'options': ["B2B direct connect", "Cross-tenant synchronization", "Microsoft Entra B2B collaboration", "Microsoft Entra External ID for customers"]},
        {'label': "Ensures that the App1 users can authenticate by using social media accounts",
         'value': "Microsoft Entra External ID for customers",
         'options': ["B2B direct connect", "Cross-tenant synchronization", "Microsoft Entra B2B collaboration", "Microsoft Entra External ID for customers"]}
    ],
    ('std', 35): [
        {'label': "Azure Backup",
         'value': "A security PIN",
         'options': ["Access policies", "Access tiers", "Encryption by using platform-managed keys", "Immutable storage", "A security PIN"]},
        {'label': "Azure Storage",
         'value': "Immutable storage",
         'options': ["Access policies", "Access tiers", "Encryption by using platform-managed keys", "Immutable storage", "A security PIN"]}
    ],
    ('std', 37): [
        {'label': "Group1",
         'value': "A Conditional Access policy",
         'options': ["A Conditional Access policy", "A sign-in risk policy in Microsoft Entra ID Protection", "A user risk policy in Microsoft Entra ID Protection", "Microsoft Defender for Office 365"]},
        {'label': "Group2",
         'value': "A compliance policy in Intune",
         'options': ["A compliance policy in Intune", "A configuration profile in Intune", "A Defender for Endpoint attack surface reduction (ASR) rule", "An endpoint security policy"]}
    ],
    ('std', 39): [
        {'label': "Service",
         'value': "Azure Key Vault",
         'options': ["Azure Key Vault", "Microsoft Entra ID Protection", "Privileged Identity Management (PIM)"]},
        {'label': "Authentication method",
         'value': "Managed identity",
         'options': ["Certificate", "Group managed service account (gMSA)", "Guest account", "Managed identity"]}
    ],
    ('std', 41): [
        {'label': "Identify the sites by using",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint", "Microsoft Defender Vulnerability Management"]},
        {'label': "Prevent the users from connecting to the sites by using",
         'value': "Microsoft Defender for Endpoint",
         'options': ["Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint", "Microsoft Defender Vulnerability Management"]}
    ],
    ('std', 44): [
        {'label': "Pricing tier",
         'value': "Standard V2",
         'options': ["Basic V2", "Consumption", "Standard V2"]},
        {'label': "Scope",
         'value': "Product",
         'options': ["API", "Product", "Workspace"]}
    ],
    ('std', 50): [
        {'label': "Identify data exfiltration attempts",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint", "Microsoft Defender for Identity", "Microsoft Defender for Office 365"]},
        {'label': "Block Teams messages",
         'value': "Microsoft Defender for Office 365",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint", "Microsoft Defender for Identity", "Microsoft Defender for Office 365"]}
    ],
    ('std', 53): [
        {'label': "Compliant devices",
         'value': "Office1 and Office2",
         'options': ["Office1 only", "Office2 only", "Office1 and Office2"]},
        {'label': "Noncompliant devices",
         'value': "Office2 only",
         'options': ["Office1 only", "Office2 only", "Office1 and Office2"]}
    ],
    ('std', 58): [
        {'label': "When a user downloads a file from SharePoint Online, a label must be applied to the file in real time based on the file's contents",
         'value': "File policy",
         'options': ["Activity policy", "File policy", "Session policy"]},
        {'label': "Only users that use Intune-compliant devices must be able to sign in to Dropbox",
         'value': "Access policy",
         'options': ["Access policy", "Activity policy", "OAuth app policy"]}
    ],
    ('std', 62): [
        {'label': "Scope",
         'value': "/providers/microsoft.management/managementGroups/Mgmt1 AND /providers/microsoft.management/managementGroups/Mgmt2",
         'options': ["/", "/providers/microsoft.management/managementGroups/<Entra Tenant GUID>", "/providers/microsoft.management/managementGroups/Mgmt1 AND /providers/microsoft.management/managementGroups/Mgmt2"]},
        {'label': "Minimum number of assignments",
         'value': "2",
         'options': ["1", "2", "30"]}
    ],
    ('std', 66): [
        {'label': "Global Secure Access apps",
         'value': "One enterprise application",
         'options': ["One enterprise application", "One Quick Access app", "Five enterprise applications", "Five Quick Access apps"]},
        {'label': "Private network connectors",
         'value': "2",
         'options': ["1", "2", "5", "10"]}
    ],
    ('std', 68): [
        {'label': "Identity type",
         'value': "Service principal",
         'options': ["Service principal", "System-assigned managed identity", "User-assigned managed identity"]},
        {'label': "Signal source",
         'value': "Microsoft Entra ID Protection",
         'options': ["Client app", "Device platform", "Microsoft Entra ID Protection"]}
    ],
    ('std', 75): [
        {'label': "Number of workspaces",
         'value': "3",
         'options': ["1", "2", "3", "4"]},
        {'label': "Service",
         'value': "Azure Lighthouse",
         'options': ["Azure Arc", "Azure Bastion", "Azure Lighthouse", "Azure Private Link"]}
    ],
    ('std', 79): [
        {'label': "To detect vulnerability scans of the apps",
         'value': "Microsoft Defender for App Service",
         'options': ["Azure WAF", "Microsoft Defender External Attack Surface Management (Defender EASM)", "Microsoft Defender for App Service", "Microsoft Defender for Cloud Apps"]},
        {'label': "To detect whether newly deployed apps are vulnerable to attack",
         'value': "Microsoft Defender External Attack Surface Management (Defender EASM)",
         'options': ["Azure WAF", "Microsoft Defender External Attack Surface Management (Defender EASM)", "Microsoft Defender for App Service", "Microsoft Defender for Cloud Apps"]}
    ],
    ('std', 90): [
        {'label': "Blobs",
         'value': "User delegation shared access signatures (SAS)",
         'options': ["Account shared access signatures (SAS)", "Microsoft Entra Domain Services", "Service shared access signatures (SAS)", "User delegation shared access signatures (SAS)"]},
        {'label': "Shares",
         'value': "Microsoft Entra Domain Services",
         'options': ["Account shared access signatures (SAS)", "Microsoft Entra Domain Services", "Service shared access signatures (SAS)", "User delegation shared access signatures (SAS)"]}
    ],
    ('std', 93): [
        {'label': "For update management, use",
         'value': "Azure Update Manager",
         'options': ["Azure Automanage", "Azure Update Manager", "System Center Updates Publisher"]},
        {'label': "On the on-premises operating systems, install",
         'value': "The Azure Connected Machine agent",
         'options': ["Azure Monitor Agent", "The Azure Connected Machine agent", "Azure VPN client"]}
    ],
    ('std', 102): [
        {'label': "Segments",
         'value': "3",
         'options': ["2", "3", "4"]},
        {'label': "Policies",
         'value': "2",
         'options': ["2", "3", "4"]}
    ],
    ('std', 105): [
        {'label': "Location",
         'value': "Sub2 in the East US Azure region",
         'options': ["Sub1 in the East US Azure region", "Sub2 in the East US Azure region", "Sub1 in the West US Azure region", "Sub2 in the West US Azure region"]},
        {'label': "Role",
         'value': "Reader",
         'options': ["Contributor", "Owner", "Reader"]}
    ],
    ('std', 110): [
        {'label': "Endpoint type",
         'value': "Azure Instance Metadata Service (IMDS)",
         'options': ["Azure Instance Metadata Service (IMDS)", "Microsoft Graph REST API v1.0", "Microsoft Identity Platform OAuth 2.0 access token"]},
        {'label': "Identity type",
         'value': "User-assigned managed identity",
         'options': ["Service principal", "System-assigned managed identity", "User-assigned managed identity"]}
    ],
    ('std', 116): [
        {'label': "Use",
         'value': "Automation rules",
         'options': ["Analytics rules", "Automation rules", "Investigation graphs"]},
        {'label': "Trigger type",
         'value': "Incident",
         'options': ["Alert", "Entity", "Incident"]}
    ],
    ('std', 120): [
        {'label': "Storage blobs",
         'value': "Data Map",
         'options': ["Compliance Manager", "Data Map", "Insider risk management", "The Information Protection scanner"]},
        {'label': "Shared folders",
         'value': "The Information Protection scanner",
         'options': ["Compliance Manager", "Data Map", "Insider risk management", "The Information Protection scanner"]}
    ],
    ('std', 128): [
        {'label': "To connect the Azure data sources to Microsoft Information Protection",
         'value': "Azure Purview",
         'options': ["Azure Purview", "Endpoint data loss prevention", "Microsoft Defender for Cloud Apps", "Microsoft Information Protection"]},
        {'label': "To triage security alerts related to resources that contain PII data",
         'value': "Microsoft Defender for Cloud",
         'options': ["Azure Monitor", "Endpoint data loss prevention", "Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps"]}
    ],
    ('std', 132): [
        {'label': "Use",
         'value': "Microsoft Purview Compliance Manager",
         'options': ["Microsoft Defender for Cloud regulatory compliance", "Microsoft Purview Audit (Premium)", "Microsoft Purview Compliance Manager", "Microsoft Priva Privacy Risk Management"]},
        {'label': "Additional costs",
         'value': "Licenses for premium regulatory templates",
         'options': ["Microsoft Priva Privacy Risk Management licenses", "Microsoft Purview Data Map capacity units", "Microsoft Syntex pay-as-you-go billing", "Licenses for premium regulatory templates"]}
    ],
    ('std', 141): [
        {'label': "Deleted backups",
         'value': "Soft delete of backups",
         'options': ["A security PIN for critical operations", "Encryption by using a customer-managed key", "Multi-user authorization by using Resource Guard", "Soft delete of backups"]},
        {'label': "Disabled backups",
         'value': "A security PIN for critical operations",
         'options': ["A security PIN for critical operations", "Encryption by using a customer-managed key", "Multi-user authorization by using Resource Guard", "Soft delete of backups"]}
    ],
    ('std', 144): [
        {'label': "RBAC roles",
         'value': "Workspaces",
         'options': ["Products", "Subscriptions", "Workspaces"]},
        {'label': "Keys",
         'value': "Subscriptions",
         'options': ["Products", "Subscriptions", "Workspaces"]}
    ],
    ('std', 148): [
        {'label': "Pre-deployment",
         'value': "Static application security testing (SAST)",
         'options': ["Dynamic application security testing (DAST)", "Penetration testing", "Security smoke testing", "Static application security testing (SAST)"]},
        {'label': "Post-deployment to the test environment",
         'value': "Dynamic application security testing (DAST)",
         'options': ["Dynamic application security testing (DAST)", "Security acceptance testing", "Security smoke testing", "Static application security testing (SAST)"]}
    ],
    ('std', 155): [
        {'label': "To minimize the number of events",
         'value': "Create Data Collection rules (DCRs)",
         'options': ["Create Data Collection rules (DCRs)", "Filter Microsoft Sentinel scheduled query rules", "Set a daily cap for WS1"]},
        {'label': "To minimize the number of Microsoft Entra identities, enable",
         'value': "System-assigned managed identities for the on-premises servers and user-assigned managed identities for the Azure virtual machines",
         'options': ["System-assigned managed identities for all the on-premises servers and Azure virtual machines", "System-assigned managed identities for the on-premises servers and user-assigned managed identities for the Azure virtual machines", "User-assigned managed identities for all the on-premises servers and Azure virtual machines", "User-assigned identities for the on-premises servers and system-assigned identities for the Azure virtual machines"]}
    ],
    ('std', 158): [
        {'label': "For the VDI",
         'value': "Add the Defender for Endpoint onboarding script to the virtual machine template",
         'options': ["Add the Defender for Endpoint onboarding script to the virtual machine template", "Deploy Defender for Endpoint by using a custom Group Policy Object (GPO)", "Onboard the virtual machine template to Defender for Endpoint"]},
        {'label': "For Azure Virtual Desktop",
         'value': "Add the Defender for Endpoint onboarding script to the golden image",
         'options': ["Add the Defender for Endpoint onboarding script to the golden image", "Deploy Defender for Endpoint by using a custom Group Policy Object (GPO)", "Onboard the golden image to Defender for Endpoint"]}
    ],
    ('std', 159): [
        {'label': "Inspection method",
         'value': "Fingerprint",
         'options': ["Exact data match (EDM)", "Fingerprint", "Trainable classifier"]},
        {'label': "Option",
         'value': "Authentication context",
         'options': ["Authentication context", "Authentication strength", "Custom control"]}
    ],
    ('std', 161): [
        {'label': "Resource type to provision",
         'value': "Azure Front Door",
         'options': ["Azure Application Gateway", "Azure Firewall Premium", "Azure Front Door", "Microsoft Defender for App Service"]},
        {'label': "Option to enable",
         'value': "Azure Web Application Firewall (WAF)",
         'options': ["Azure Firewall web categories", "Azure Web Application Firewall (WAF)", "Intrusion detection and prevention system (IDPS)", "Threat intelligence-based filtering"]}
    ],
    ('std', 162): [
        {'label': "Manage NSG rules by using",
         'value': "Just-in-time (JIT) VM access",
         'options': ["Azure Automation", "Azure Bastion", "Just-in-time (JIT) VM access"]},
        {'label': "Only allow SSH connections to the jump servers from",
         'value': "Any public IP addresses provided before the connection is established",
         'options': ["Any public IP addresses provided before the connection is established", "AzureBastionSubnet", "GatewaySubnet"]}
    ],
    ('std', 168): [
        {'label': "Identity Governance feature",
         'value': "Access reviews",
         'options': ["Access reviews", "Azure AD Privileged Identity Management (PIM)", "Entitlement management", "Lifecycle workflows"]},
        {'label': "Project team configuration",
         'value': "Azure AD, create a security group for each project and enable group writeback for each group",
         'options': ["Enable group writeback for the existing synced groups", "From Azure AD, create a new cloud-only security group for each project", "Azure AD, create a security group for each project and enable group writeback for each group"]}
    ],
    ('std', 178): [
        {'label': "Service",
         'value': "Microsoft Entra ID Protection",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Identity", "Microsoft Entra ID Protection"]},
        {'label': "License type",
         'value': "Microsoft Entra Workload ID Premium",
         'options': ["Microsoft Entra ID P1", "Microsoft Entra ID P2", "Microsoft Entra Workload ID Premium"]}
    ],
    ('std', 185): [
        {'label': "For the network controls",
         'value': "Microsoft Defender for Cloud",
         'options': ["Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint"]},
        {'label': "For the authorization controls",
         'value': "Microsoft Entra Privileged Identity Management (PIM)",
         'options': ["Microsoft Entra Privileged Identity Management (PIM)", "Microsoft Purview Privileged Access Management", "Microsoft Entra Permissions Management"]}
    ],
    ('std', 186): [
        {'label': "Commit the code",
         'value': "Static application security testing (SAST)",
         'options': ["Dynamic application security testing (DAST)", "Penetration testing", "Smoke testing", "Static application security testing (SAST)"]},
        {'label': "Build and test",
         'value': "Dynamic application security testing (DAST)",
         'options': ["Dynamic application security testing (DAST)", "Penetration testing", "Smoke testing", "Static application security testing (SAST)"]}
    ],
    ('std', 190): [
        {'label': "Developer",
         'value': "Specialized security",
         'options': ["Enterprise security", "Privileged security", "Specialized security"]},
        {'label': "Standard user",
         'value': "Enterprise security",
         'options': ["Enterprise security", "Privileged security", "Specialized security"]},
        {'label': "IT administrator",
         'value': "Privileged security",
         'options': ["Enterprise security", "Privileged security", "Specialized security"]}
    ],
    ('std', 198): [
        {'label': "Azure service",
         'value': "Azure Key Vault Managed HSM",
         'options': ["Azure Key Vault Premium SKU", "Azure Key Vault Standard SKU", "Azure Key Vault Managed HSM"]},
        {'label': "Authorization mechanism",
         'value': "A single vault with role-based access control (RBAC) authorization",
         'options': ["20 vaults with role-based access control (RBAC) authorization", "A single vault with role-based access control (RBAC) authorization", "A single vault with role-based access control (RBAC) authorization and access policy-based authorization"]}
    ],
    ('std', 199): [
        {'label': "An attacker attempts to exfiltrate data to external websites",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Identity", "Microsoft Defender for Office 365"]},
        {'label': "An attacker attempts lateral movement across domain-joined computers",
         'value': "Microsoft Defender for Identity",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Identity", "Microsoft Defender for Office 365"]}
    ],
    ('std', 201): [
        {'label': "Pool1",
         'value': "Infrastructure encryption",
         'options': ["Infrastructure encryption", "Server-side encryption (SSE)", "Transparent Data Encryption (TDE)"]},
        {'label': "Serverless SQL pool",
         'value': "Infrastructure encryption",
         'options': ["Infrastructure encryption", "Server-side encryption (SSE)", "Transparent Data Encryption (TDE)"]}
    ],
    ('std', 202): [
        {'label': "Git workflow",
         'value': "Protected branches",
         'options': ["Azure Key Vault", "Custom roles for build agents", "Protected branches", "Resource locks in Azure"]},
        {'label': "Secure deployment credentials",
         'value': "Azure Key Vault",
         'options': ["Azure Key Vault", "Custom roles for build agents", "Protected branches", "Resource locks in Azure"]}
    ],
    ('std', 204): [
        {'label': "Integrate Microsoft Sentinel with a third-party security vendor",
         'value': "A threat intelligence connector",
         'options': ["Custom entity activities", "A playbook", "A threat detection rule", "A threat indicator", "A threat intelligence connector"]},
        {'label': "Automatically generate incidents",
         'value': "A threat detection rule",
         'options': ["Custom entity activities", "A playbook", "A threat detection rule", "A threat indicator", "A threat intelligence connector"]}
    ],
    ('std', 206): [
        {'label': "Uploading the code to repositories",
         'value': "GitHub Enterprise",
         'options': ["Azure Boards", "Azure Pipelines", "GitHub Enterprise", "Microsoft Defender for Cloud"]},
        {'label': "Building containers",
         'value': "Azure Pipelines",
         'options': ["Azure Boards", "Azure Pipelines", "GitHub Enterprise", "Microsoft Defender for Cloud"]}
    ],
    ('std', 207): [
        {'label': "For the SQL audit logs",
         'value': "A Log Analytics workspace",
         'options': ["A Log Analytics workspace", "Azure Application Insights", "Microsoft Defender for SQL", "Microsoft Sentinel"]},
        {'label': "For the Windows Security logs",
         'value': "A Log Analytics workspace",
         'options': ["A Log Analytics workspace", "Application Insights", "Microsoft Defender for servers", "Microsoft Sentinel"]},
        {'label': "For the App Service audit logs",
         'value': "A Log Analytics workspace",
         'options': ["A Log Analytics workspace", "Application Insights", "Microsoft Defender for App Service", "Microsoft Sentinel"]}
    ],
    ('std', 210): [
        {'label': "Delegate permissions by using",
         'value': "Azure Lighthouse",
         'options': ["Azure Blueprints", "Azure Lighthouse", "Azure Sphere"]},
        {'label': "Microsoft Sentinel feature",
         'value': "Incidents",
         'options': ["Analytics rules", "Incidents", "Workbooks"]}
    ],
    ('std', 212): [
        {'label': "DLP",
         'value': "Microsoft Purview",
         'options': ["Azure Data Catalog", "Azure Data Explorer", "Microsoft Purview"]},
        {'label': "UEBA",
         'value': "Microsoft Defender for Identity",
         'options': ["Azure AD Identity Protection", "Microsoft Defender for Identity", "Microsoft Entra Verified ID"]}
    ],
    ('std', 226): [
        {'label': "Infrastructure scanning",
         'value': "Build and test",
         'options': ["Build and test", "Commit the code", "Go to production", "Operate", "Plan and develop"]},
        {'label': "Static application security testing",
         'value': "Commit the code",
         'options': ["Build and test", "Commit the code", "Go to production", "Operate", "Plan and develop"]}
    ],
    ('std', 228): [
        {'label': "For the inbound connections",
         'value': "Azure Web Application Firewall (WAF)",
         'options': ["Application security groups", "Azure Firewall", "Azure Web Application Firewall (WAF)", "Microsoft Entra application proxy", "Network security groups (NSGs)"]},
        {'label': "For the outbound connections",
         'value': "Azure Firewall",
         'options': ["Application security groups", "Azure Firewall", "Azure Web Application Firewall (WAF)", "Microsoft Entra application proxy", "Network security groups (NSGs)"]}
    ],
    ('std', 231): [
        {'label': "To optimize the connection between the users and the application proxy, deploy",
         'value': "A connector to the default connector group and a connector to a new connector group",
         'options': ["A connector to the default connector group and a connector to a new connector group", "Two connectors to a new connector group", "Two connectors to the default connector group"]},
        {'label': "To optimize the connection between the application proxy and the connectors, use",
         'value': "ExpressRoute with Microsoft peering",
         'options': ["ExpressRoute with Microsoft peering", "ExpressRoute with Microsoft peering and the premium add-on", "ExpressRoute with private peering"]}
    ],
    ('std', 232): [
        {'label': "App1",
         'value': "Azure Application Gateway Web Application Firewall policies",
         'options': ["Azure AD B2B authentication with Conditional Access", "Azure AD B2C custom policies with Conditional Access", "Azure Application Gateway Web Application Firewall policies", "Azure Firewall", "Azure VPN Gateway with network security group rules", "Azure VPN Point-to-Site connections"]},
        {'label': "App2",
         'value': "Azure AD B2C custom policies with Conditional Access",
         'options': ["Azure AD B2B authentication with Conditional Access", "Azure AD B2C custom policies with Conditional Access", "Azure Application Gateway Web Application Firewall policies", "Azure Firewall", "Azure VPN Gateway with network security group rules", "Azure VPN Point-to-Site connections"]}
    ],
    ('std', 238): [
        {'label': "Manage NSG rules by using",
         'value': "Just-in-time (JIT) VM access",
         'options': ["Azure Automation", "Azure Bastion", "Just-in-time (JIT) VM access"]},
        {'label': "Only allow SSH connections to the jump servers from",
         'value': "Any public IP addresses provided before the connection is established",
         'options': ["Any public IP addresses provided before the connection is established", "AzureBastionSubnet", "GatewaySubnet"]}
    ],
    ('std', 240): [
        {'label': "In Azure, deploy",
         'value': "Azure Monitor Data collection rules (DCRs)",
         'options': ["Azure Monitor data collection endpoints", "Azure Monitor Data collection rules (DCRs)", "Microsoft Defender for Cloud data collection settings"]},
        {'label': "On the virtual machines, install",
         'value': "the Azure Connected Machine agent",
         'options': ["the Azure Connected Machine agent", "the Network Controller role", "the Azure Pipelines agent"]}
    ],
    ('std', 244): [
        {'label': "For the on-premises datacenter",
         'value': "Microsoft Azure Backup Server (MABS)",
         'options': ["An Azure virtual machine extension", "Microsoft Azure Backup Server (MABS)", "The Microsoft Azure Recovery Services (MARS) agent"]},
        {'label': "For Sub1",
         'value': "A Recovery Services vault",
         'options': ["A Recovery Services vault", "An Azure Backup vault", "Azure Storage block blobs"]}
    ],
    ('std', 246): [
        {'label': "Role",
         'value': "Privileged Role Administrator",
         'options': ["Global Administrator", "Privileged Role Administrator", "Security Administrator"]},
        {'label': "Tool",
         'value': "Access reviews",
         'options': ["Access packages", "Access reviews", "Lifecycle workflows"]}
    ],
    ('std', 247): [
        {'label': "All pull requests must be enforced",
         'value': "Protected branches",
         'options': ["Environments", "Protected branches", "Resource locks"]},
        {'label': "All deployments to production must be approved",
         'value': "Environments",
         'options': ["Environments", "Resource locks", "Triggers"]}
    ],
    ('std', 248): [
        {'label': "The number of failed sign-in attempts that trigger a lockout",
         'value': "Microsoft Entra ID only",
         'options': ["AD DS only", "Microsoft Entra ID only", "AD DS and Microsoft Entra ID"]},
        {'label': "The duration of the lockout",
         'value': "Microsoft Entra ID only",
         'options': ["AD DS only", "Microsoft Entra ID only", "AD DS and Microsoft Entra ID"]}
    ],
    ('std', 255): [
        {'label': "Automatically identify threats found in AWS CloudTrail events",
         'value': "Microsoft Sentinel",
         'options': ["Azure Arc", "Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Sentinel"]},
        {'label': "Enforce security settings on AWS virtual machines by using Azure policies",
         'value': "Microsoft Defender for Cloud",
         'options': ["Azure Arc", "Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Sentinel"]}
    ],
    ('std', 256): [
        {'label': "For the customers",
         'value': "Azure AD B2C authentication",
         'options': ["Azure AD B2B authentication with access package assignments", "Azure AD B2C authentication", "Federation in Azure AD Connect with Active Directory Federation Services", "Pass-through authentication in Azure AD Connect", "Password hash synchronization in Azure AD Connect"]},
        {'label': "For the partners",
         'value': "Azure AD B2B authentication with access package assignments",
         'options': ["Azure AD B2B authentication with access package assignments", "Azure AD B2C authentication", "Federation in Azure AD Connect with Active Directory Federation Services", "Pass-through authentication in Azure AD Connect", "Password hash synchronization in Azure AD Connect"]}
    ],
    ('std', 260): [
        {'label': "For the IoT Edge devices",
         'value': "Microsoft Defender for IoT",
         'options': ["Azure Arc", "Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Endpoint", "Microsoft Defender for IoT"]},
        {'label': "For the AWS EC2 instances",
         'value': "Microsoft Defender for Cloud and Azure Arc",
         'options': ["Azure Arc only", "Microsoft Defender for Cloud and Azure Arc", "Microsoft Defender for Cloud Apps only", "Microsoft Defender for Cloud only", "Microsoft Defender for Endpoint and Azure Arc", "Microsoft Defender for Endpoint only"]}
    ],
    ('std', 263): [
        {'label': "Custom dashboards",
         'value': "Workbooks",
         'options': ["Notebooks", "Playbooks", "Workbooks"]},
        {'label': "Automated responses",
         'value': "Playbooks",
         'options': ["Notebooks", "Playbooks", "Workbooks"]}
    ],
    ('std', 267): [
        {'label': "EDR",
         'value': "Onboard the servers to Defender for Cloud",
         'options': ["Add a Microsoft Sentinel data connector for Azure Active Directory (Azure AD)", "Add a Microsoft Sentinel data connector for Microsoft Defender for Cloud Apps", "Onboard the servers to Azure Arc", "Onboard the servers to Defender for Cloud"]},
        {'label': "SOAR",
         'value': "Configure Microsoft Sentinel playbooks",
         'options': ["Configure Microsoft Sentinel analytics rules", "Configure Microsoft Sentinel playbooks", "Configure regulatory compliance standards in Defender for Cloud", "Configure workflow automation in Defender for Cloud"]}
    ],
    ('std', 269): [
        {'label': "Service",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["Microsoft Defender for Cloud Apps", "Microsoft Defender for Office 365", "Microsoft Purview Data Loss Prevention (DLP)", "Microsoft Purview Information Protection"]},
        {'label': "Policy",
         'value': "An anomaly detection policy",
         'options': ["A data loss prevention (DLP) policy applied to SharePoint Online", "A file policy", "An anomaly detection policy", "An Endpoint data loss prevention (Endpoint DLP) policy"]}
    ],
    ('std', 270): [
        {'label': "Inbound connectivity",
         'value': "Private endpoints",
         'options': ["Private endpoints", "Service endpoints", "Static IP restrictions", "Virtual network integration"]},
        {'label': "Outbound connectivity",
         'value': "Virtual network integration",
         'options': ["Private endpoint", "Service endpoint", "Static IP restrictions", "Virtual network integration"]}
    ],
    ('std', 271): [
        {'label': "Service",
         'value': "Microsoft Defender for Office 365",
         'options': ["Azure AD Identity Protection", "Microsoft Defender for DNS", "Microsoft Defender for Office 365", "Microsoft Purview"]},
        {'label': "Policy type",
         'value': "Anti-phishing",
         'options': ["Anti-phishing", "Anti-spam", "Data loss prevention (DLP)", "Insider risk management"]}
    ],
    ('std', 273): [
        {'label': "To optimize the connection between the users and the application proxy, deploy",
         'value': "Two connectors to the default connector group",
         'options': ["A connector to the default connector group and a connector to a new connector group", "Two connectors to a new connector group", "Two connectors to the default connector group"]},
        {'label': "To optimize the connection between the connector and App1, use",
         'value': "ExpressRoute with private peering",
         'options': ["ExpressRoute with Microsoft peering", "ExpressRoute with Microsoft peering and the premium add-on", "ExpressRoute with private peering"]}
    ],
    ('std', 279): [
        {'label': "Automatically identifies and stops external, brute force attacks against accounts",
         'value': "Microsoft Entra ID Protection",
         'options': ["Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Identity", "Microsoft Entra ID Identity Governance", "Microsoft Entra ID Protection"]},
        {'label': "Automatically identifies and stops external attacks that use an internal account to exfiltrate data from SharePoint Online sites",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["Microsoft Defender for Cloud", "Microsoft Defender for Cloud Apps", "Microsoft Defender for Identity", "Microsoft Entra ID Identity Governance", "Microsoft Entra ID Protection"]}
    ],
    ('std', 285): [
        {'label': "Authorization mechanism",
         'value': "Attribute-based access control (ABAC)",
         'options': ["Access control list (ACL)", "Attribute-based access control (ABAC)", "Shared access signature (SAS)"]},
        {'label': "Resource type",
         'value': "Blob",
         'options': ["Blob", "File", "Table"]}
    ],
    ('std', 287): [
        {'label': "Property to add",
         'value': "roleDefinitionIds",
         'options': ["conflictEffect", "existenceCondition", "roleDefinitionIds"]},
        {'label': "Effect to use",
         'value': "Modify",
         'options': ["append", "Modify", "mutate"]}
    ],
    ('std', 291): [
        {'label': "Pool1",
         'value': "Monthly",
         'options': ["Weekly", "Monthly", "Quarterly"]},
        {'label': "Pool2",
         'value': "Weekly",
         'options': ["Weekly", "Monthly", "Quarterly"]}
    ],
    # These four look like drag-and-drop at a glance (a pool on the left, fixed
    # target rows on the right), but each target row only ever takes one value
    # from that same pool — exactly what a drop-down already does. No new
    # rendering was needed for them, just entries here like everything above.
    ('std', 94): [
        {'label': "Use the Microsoft Cloud Adoption Framework for Azure to evaluate compliance with cloud governance policies",
         'value': "Microsoft Defender for Cloud",
         'options': ["Azure Advisor", "Microsoft cloud security benchmark (MCSB)", "Microsoft Defender for Cloud",
                     "Microsoft Defender Vulnerability", "Microsoft Intune", "Microsoft Sentinel"]},
        {'label': "Use the Azure Well-Architected Framework to secure individual workloads",
         'value': "Microsoft Defender Vulnerability",
         'options': ["Azure Advisor", "Microsoft cloud security benchmark (MCSB)", "Microsoft Defender for Cloud",
                     "Microsoft Defender Vulnerability", "Microsoft Intune", "Microsoft Sentinel"]}
    ],
    ('std', 174): [
        {'label': "Assume breach", 'value': "Segmenting access",
         'options': ["Business continuity", "Data classification", "Just-in-time (JIT) access", "Segmenting access"]},
        {'label': "Verify explicitly", 'value': "Data classification",
         'options': ["Business continuity", "Data classification", "Just-in-time (JIT) access", "Segmenting access"]},
        {'label': "Use least privilege access", 'value': "Just-in-time (JIT) access",
         'options': ["Business continuity", "Data classification", "Just-in-time (JIT) access", "Segmenting access"]}
    ],
    ('std', 205): [
        {'label': "For brute force password attacks", 'value': "Azure AD Password Protection",
         'options': ["Azure AD Password Protection", "Extranet Smart Lockout (ESL)", "Password hash synchronization"]},
        {'label': "For leaked credentials", 'value': "Password hash synchronization",
         'options': ["Azure AD Password Protection", "Extranet Smart Lockout (ESL)", "Password hash synchronization"]}
    ],
    ('std', 225): [
        {'label': "User accounts that were potentially compromised",
         'value': "Azure Active Directory (Azure AD) Identity Protection",
         'options': ["A data loss prevention (DLP) policy", "Azure Active Directory (Azure AD) Conditional Access",
                     "Azure Active Directory (Azure AD) Identity Protection", "Microsoft Defender for Cloud",
                     "Microsoft Defender for Cloud Apps"]},
        {'label': "Users performing bulk file downloads from SharePoint Online",
         'value': "Microsoft Defender for Cloud Apps",
         'options': ["A data loss prevention (DLP) policy", "Azure Active Directory (Azure AD) Conditional Access",
                     "Azure Active Directory (Azure AD) Identity Protection", "Microsoft Defender for Cloud",
                     "Microsoft Defender for Cloud Apps"]}
    ],
    # A Yes/No table reduces the same way: each statement is a box with a fixed
    # two-item option list rather than a full sentence, so it renders as one
    # more drop-down instead of needing its own radio-button UI for a single item.
    ('std', 284): [
        {'label': "To enable MUA for Vault1, a resource guard must be deployed to Sub1.",
         'value': "No", 'options': ["Yes", "No"]},
        {'label': "A user in Group2 must approve changes made by a user in Group1 to the backup policies of Vault1.",
         'value': "Yes", 'options': ["Yes", "No"]},
        {'label': "A user in Group1 that activates Assignment1 can disable soft delete for the backups of Vault1, without the approval of a user in Group2.",
         'value': "No", 'options': ["Yes", "No"]}
    ],
}
AREA_NOTE = ('The choices for this item were supplied from outside the dump; the dump itself '
             'records the answer only as the picture shown above. Grading uses those choices.')

PRIOR_NOTE = ('The dump records this answer as a picture, shown above. The values below come '
              'from a text export of the same dump, which spelled them out. No list of '
              'alternatives survives anywhere, so each drop-down offers this item’s own '
              'values — match each one to its box.')

# Ordering items: move a subset of a pool of actions into the answer area and
# arrange them correctly. `pool` is every action offered (including
# distractors never used in a correct answer); `answers` is the list of
# sequences that count as correct — almost always just one, except where the
# source itself says "more than one order... is correct".
ORDER_ITEMS = {
    ('std', 77): {
        'pool': ["Implement DevOps integration.", "Discover and protect IoT devices.",
                 "Explicitly validate trust for all access requests.",
                 "Apply provisions for ransomware recovery readiness.", "Classify and protect data."],
        'answers': [["Explicitly validate trust for all access requests.",
                      "Apply provisions for ransomware recovery readiness.", "Classify and protect data."]],
    },
    ('std', 156): {
        'pool': ["Assess the current situation and identify the scope.",
                 "Identify which line-of-business (LOB) apps are unavailable due to a ransomware incident.",
                 "Identify the compromise recovery process.",
                 "Implement a comprehensive strategy to reduce the risk of privileged access compromise.",
                 "Update organizational processes to manage major ransomware events and streamline outsourcing to avoid friction."],
        'answers': [["Assess the current situation and identify the scope.",
                      "Identify which line-of-business (LOB) apps are unavailable due to a ransomware incident.",
                      "Identify the compromise recovery process."]],
    },
    ('std', 220): {
        'pool': ["Modify the target resources of Policy1.",
                 "For the Microsoft Entra tenant, create an authentication strength.",
                 "For the Microsoft Entra tenant, create an authentication context.",
                 "Modify the conditions of Policy1.", "Configure a sensitivity label for Site1."],
        # The item's own note says more than one order is accepted: the
        # authentication context has to exist before either of the other two
        # steps can reference it, but those two don't depend on each other.
        'answers': [
            ["For the Microsoft Entra tenant, create an authentication context.",
             "Modify the conditions of Policy1.", "Configure a sensitivity label for Site1."],
            ["For the Microsoft Entra tenant, create an authentication context.",
             "Configure a sensitivity label for Site1.", "Modify the conditions of Policy1."],
        ],
    },
    ('std', 239): {
        'pool': ["Establish ransomware recovery readiness.", "Implement disaster recovery.",
                 "Establish visibility.", "Enable additional protection and detection controls.",
                 "Enable automation."],
        'answers': [["Establish visibility.", "Enable additional protection and detection controls.",
                      "Enable automation."]],
    },
    ('std', 266): {
        'pool': ["Create an Azure Backup vault.", "From RG1, create a resource lock.",
                  "Create a Recovery Services vault.", "Enable vault immutability.",
                  "Lock immutability for the vault."],
        'answers': [["Create a Recovery Services vault.", "Enable vault immutability.",
                      "Lock immutability for the vault."]],
    },
    ('std', 272): {
        'pool': ["Assign storage1 the Key Vault Reader role to access the key.",
                 "Create a managed identity and assign it to storage1.",
                 "Create and assign an access policy for storage1.",
                 "Configure Azure Storage encryption with customer-managed keys.",
                 "Create and assign a Key Vault access policy.",
                 "Create a managed identity and assign it to AKV1."],
        'answers': [["Create a managed identity and assign it to storage1.",
                      "Create and assign a Key Vault access policy.",
                      "Configure Azure Storage encryption with customer-managed keys."]],
    },
}
ORDER_NOTE = ('The choices and their order were supplied from outside the dump; the dump itself '
              'records the answer only as the picture shown above. Grading uses that order.')

# Answer-area values recovered from the earlier text-only export of this dump,
# keyed "<section>/<number>".
_prior = json.load(open(paths.PRIOR_AREAS, encoding='utf-8'))
PRIOR_BOXES = {(k.split('/')[0], int(k.split('/')[1])): v for k, v in _prior.items()}


def conv(nodes):
    """Map extracted nodes onto what the page renders, dropping images that
    were filtered out of the re-encoded set."""
    out = []
    for n in nodes:
        if 'img' in n:
            e = imgmap.get(n['img'])
            if not e:
                continue
            out.append({'img': 'img/' + e[0], 'w': e[2], 'h': e[3]})
        else:
            t = n['p'].strip()
            if t:
                out.append({'p': t})
    return out


items = []
for q in parsed['questions']:
    sec, num = q['sec'], q['num']
    item = {'n': len(items) + 1, 'sec': sec, 'num': num, 'c': q['c']}
    if sec in CASE_META:
        item['cs'] = CASE_META[sec]

    body = conv(q['body'])
    item['body'] = body
    # A one-line summary for the review screen and the resume banner.
    first = next((n['p'] for n in reversed(body) if 'p' in n and n['p'].endswith('?')), None)
    item['q'] = first or next((n['p'] for n in body if 'p' in n), '(see question)')

    letters = [x for x in re.split(r'[,\s]+', q['a'] or '') if x]
    valid = [l for l, _ in q['o']]
    if q['o'] and letters and all(x in valid for x in letters):
        item['o'] = [t for _, t in q['o']]
        item['a'] = ' '.join(letters)
    elif (sec, num) in ANSWER_AREAS:
        boxes = ANSWER_AREAS[(sec, num)]
        for b in boxes:
            assert b['value'] in b['options'], 'answer area %s %d is inconsistent' % (sec, num)
        item['boxes'] = boxes
        item['keynote'] = AREA_NOTE
    elif (sec, num) in PRIOR_BOXES:
        # An earlier, text-only export of the same dump spelled these answer
        # areas out as "<label>: <value>" lines. The dump proper draws them, so
        # the values survive only here — keeping them means the item stays
        # gradeable, and the recorded graphic is shown alongside on reveal.
        item['boxes'] = PRIOR_BOXES[(sec, num)]
        item['keynote'] = PRIOR_NOTE
    elif (sec, num) in ORDER_ITEMS:
        order = ORDER_ITEMS[(sec, num)]
        pool_set = set(order['pool'])
        for ans in order['answers']:
            assert set(ans) <= pool_set, 'order item %s %d answer not in its own pool' % (sec, num)
            assert len(set(ans)) == len(ans), 'order item %s %d answer repeats an action' % (sec, num)
        item['order'] = order
        item['keynote'] = ORDER_NOTE

    ans = conv(q['ansimg'])
    if ans:
        item['ansimg'] = ans
    expl = conv(q['e'])
    if expl:
        item['e'] = expl
    items.append(item)

# The answer-key review is applied last, so a correction lands on the graded
# key and the displayed explanation from the same place and cannot diverge.
review_entries = review_mod.load()
index = {'%s/%d' % (i['sec'], i['num']): i for i in items}
problems = review_mod.validate(review_entries, index)
if problems:
    raise SystemExit('review.json is inconsistent:\n  ' + '\n  '.join(problems))
for key, entry in review_entries.items():
    review_mod.merge(index[key], entry)

cases = {k: conv(v) for k, v in parsed['cases'].items()}
for k, v in cases.items():
    CASE_META[k]['nodes'] = v

choice = sum(1 for i in items if 'o' in i)
match = sum(1 for i in items if 'boxes' in i)
order_n = sum(1 for i in items if 'order' in i)
info = len(items) - choice - match - order_n
print('total %d | choice %d | match %d | order %d | info %d' % (len(items), choice, match, order_n, info))
print('scored: %d' % (choice + match + order_n))
print('info items that now show a recorded answer: %d'
      % sum(1 for i in items if 'o' not in i and 'boxes' not in i and 'order' not in i and i.get('ansimg')))
print('items carrying an exhibit: %d' % sum(1 for i in items if any('img' in n for n in i['body'])))
print('items carrying an explanation: %d' % sum(1 for i in items if i.get('e')))
print('per section:', Counter(i['sec'] for i in items))
print('per domain:', Counter(i['c'] for i in items))
print('case narrative nodes:', {k: len(v) for k, v in cases.items()})
from collections import Counter as _C
_st = _C(e['status'] for e in review_entries.values())
print('review: %d of %d examined -> %s' % (len(review_entries), len(items), dict(_st)))

json.dump({'items': items, 'cases': CASE_META},
          open(paths.BANK, 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
