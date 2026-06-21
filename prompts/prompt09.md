# Prompt 9 — Connect Hermes to Discord Server (Guild)

**Phase:** 4 (Discord Integration)
**Send to:** Orchestrator

---

Server ID (also called Guild ID): [PASTE YOUR DISCORD SERVER ID HERE]

Wire the Hermes-Discord integration to this server ID.

Confirm the bot can connect and is reachable on the server.

🔍 **Get Server ID**: Enable Developer Mode in Discord (Settings → Advanced) → Right-click server → Copy Server ID (this is the Guild ID).

---

## Prerequisites (do BEFORE this prompt)
1. Create a Discord server
2. Create a Discord bot at https://discord.com/developers/applications
3. Enable Privileged Gateway Intents: Presence, Server Members, Message Content
4. Set bot permissions to Administrator
5. Invite bot to your server via OAuth2 URL
6. Delete default channels (general, rules, etc.)
7. Enable Developer Mode in Discord settings
8. Copy your User ID, Server ID
9. Run `hermes setup` and configure Discord with bot token + user ID + home channel ID

## What to Watch For
- You MUST paste your actual Discord Server ID in the prompt
- Bot should show as online in your server after this
- If bot doesn't connect, check token and intents
