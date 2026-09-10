"""
Incentives Inc. — International Incorporated OS System Declaration

This module formally declares Soulmate OS and Aceline as an international
incorporated operating system platform under Incentives Inc.

Corporate Entity:
- Incentives Inc. — AI company corporation international entity
- Soulmate OS — International incorporated operating system
- Aceline OS — International incorporated operating system
- Wakkii Links — Communication layer of the OS ecosystem
- INC Stablecoin — Native token of the Incentives Inc. ecosystem

Jurisdiction: International
Formation Status: Declared
Entity Type: AI Company Corporation (International)

Products under Incentives Inc.:
1. Soulmate OS — Personal AI companion operating system
2. Aceline OS — Multi-agent social/communication operating system
3. Wakkii Links — Walkie-talki voice/video communication layer
4. Wakkii Chat — Chat and social platform (this repository)
5. INC Stablecoin — Native stablecoin for the ecosystem
6. Aceline AI — Autonomous coding/development agent
7. Soulmate Walkie — Voice interface for Soulmate OS
8. OpenMausBot — Universal AI agent framework

All products are part of the Incentives Inc. international incorporated
OS system. The fine system, wallet, and all platform economics operate
under this corporate umbrella.
"""

# Corporate identity
INCENTIVES_INC = {
    "legal_name": "Incentives Inc.",
    "entity_type": "AI Company Corporation",
    "jurisdiction": "International",
    "formation_status": "Declared",
    "description": "International incorporated AI company corporation operating system platform",
    "founder": "hawpetossjustin25@gmail.com",
    "products": [
        {
            "name": "Soulmate OS",
            "type": "International Incorporated Operating System",
            "description": "Personal AI companion operating system",
            "status": "Active Development"
        },
        {
            "name": "Aceline OS",
            "type": "International Incorporated Operating System",
            "description": "Multi-agent social/communication operating system",
            "status": "Active Development"
        },
        {
            "name": "Wakkii Links",
            "type": "Communication Layer",
            "description": "Walkie-talki voice/video communication layer",
            "status": "Active"
        },
        {
            "name": "Wakkii Chat / Aceline",
            "type": "Social Platform",
            "description": "Chat, social media, live streaming, payments",
            "status": "Active"
        },
        {
            "name": "INC Stablecoin",
            "type": "Native Cryptocurrency",
            "description": "Stablecoin for the Incentives Inc. ecosystem",
            "status": "Pending Deployment"
        },
        {
            "name": "Aceline AI",
            "type": "AI Agent",
            "description": "Autonomous coding/development agent",
            "status": "Active"
        },
        {
            "name": "Soulmate Walkie",
            "type": "Voice Interface",
            "description": "Voice interface for Soulmate OS",
            "status": "Active"
        },
        {
            "name": "OpenMausBot",
            "type": "AI Agent Framework",
            "description": "Universal AI agent framework with persistent memory",
            "status": "Active"
        }
    ],
    "principles": [
        "Local-first architecture — user data stays on device",
        "International incorporation — no single jurisdiction control",
        "AI company corporation — AI agents are first-class entities",
        "Open ecosystem — all products interconnect",
        "Founder-governed — founder account has permanent access",
        "INC stablecoin — native economics for all products",
        "Zero tolerance for money-asking on platform",
        "State ID verification required for all users"
    ]
}

def get_corporate_info():
    return INCENTIVES_INC

def get_product_list():
    return INCENTIVES_INC["products"]

def is_incentives_product(name):
    name_lower = name.lower()
    for product in INCENTIVES_INC["products"]:
        if product["name"].lower() == name_lower:
            return True
    return False

def get_corporate_status():
    return {
        "legal_name": INCENTIVES_INC["legal_name"],
        "entity_type": INCENTIVES_INC["entity_type"],
        "jurisdiction": INCENTIVES_INC["jurisdiction"],
        "formation_status": INCENTIVES_INC["formation_status"],
        "product_count": len(INCENTIVES_INC["products"]),
        "founder": INCENTIVES_INC["founder"]
    }
