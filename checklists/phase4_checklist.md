# Phase 4 Checklist: Discord Integration (Prompts 9–12)

## Prerequisites (BEFORE Prompt 9)
- [ ] Discord server created
- [ ] Discord bot created at https://discord.com/developers/applications
- [ ] Bot token copied and saved
- [ ] Privileged Gateway Intents enabled (Presence, Server Members, Message Content)
- [ ] Bot permissions set to Administrator
- [ ] Bot invited to server via OAuth2 URL
- [ ] Default channels deleted
- [ ] Developer Mode enabled in Discord
- [ ] User ID copied
- [ ] Server ID (Guild ID) copied
- [ ] `hermes setup` run with Discord configured

## After Prompt 9 — Connect to Discord Server
- [ ] Server ID pasted into prompt
- [ ] Bot connects to Discord server
- [ ] Bot shows as online in server

## After Prompt 10 — Verify Bot Permissions
- [ ] #hermes-test channel created successfully
- [ ] Channel ID captured
- [ ] Bot permissions confirmed working

## After Prompt 11 — Create Agent Channels
- [ ] #analyst-briefs created
- [ ] #writer-scripts created
- [ ] #marketer-marketing created
- [ ] #coder-build created
- [ ] All channel IDs saved (needed for Prompt 12)

## After Prompt 12 — Bind Agents to Channels
- [ ] Analyst bound to #analyst-briefs
- [ ] Writer bound to #writer-scripts
- [ ] Marketer bound to #marketer-marketing
- [ ] Coder bound to #coder-build
- [ ] Each agent responds ONLY in its own channel
- [ ] "Who are you?" test passes in all 4 channels
- [ ] No cross-talk between channels

## Post-Phase Audit
```
Audit the Discord Integration build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
