# Intelligent TFT

A self-evolving AI agent that plays Teamfight Tactics.

Unlike traditional TFT bots that use hardcoded rules and fragile OCR coordinates, this agent uses:
- **Riot Live Client API** for game state (gold, level, HP, players)
- **Screen capture + vision** for board/shop/item reading
- **LLM decision engine** (Gemma) for strategic choices
- **Game memory** for learning and evolution across games

## Architecture

```
┌──────────────────────────────────┐
│         Riot Live Client API      │  Gold, Level, HP, Players
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│         Screen Reader             │  Screenshots → game state
│  (mss + pyautogui)               │  Shop, Board, Items, Popups
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│         Game State                │  Unified state object
│  round, gold, level, hp, shop,   │  Updated every tick
│  board, bench, items, phase      │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│         Agent                     │  Decides actions
│  Rule engine + LLM advisor       │  Buy, sell, position, items
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│         Executor                  │  Performs actions
│  pyautogui clicks/drags           │  Rate-limited, phase-aware
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│         Memory                    │  Learns over time
│  Game logs, replays, outcomes     │  Feeds back into Agent
└──────────────────────────────────┘
```

## Current Target: Set 17 (Space Gods) — Mecha Fast 8

1. **Early (1-1 → 3-7)**: Econ. Buy cheap frontline. Save to 50g.
2. **Mid (4-1)**: Level to 8. Roll for AurelionSol / TahmKench / Karma.
3. **Late**: Upgrade, level 9, optimize items.

## Setup

```bash
# macOS only for now
brew install tesseract
cd ~/intelligent-tft
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 agent.py   # Cmd+= to stop
```

## Credits & Acknowledgments

The OCR game interface layer is built on top of [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT) (GPL-3.0), a community-built TFT bot using screen reading and automation. Thanks to all its contributors:

**jfd02** (creator), Anoukshia, anthony5301, Arborym, Cr4zZyBipBiip, Dan, Filip Smets, francis, GeeseGoo, Ikerono, Jefferson Santos, joseph, PawelklosPL, Rok, stardust136

This project extends their work with:
- macOS support (Quartz, mss, pyautogui)
- Riot Live Client API integration
- Set 17 (Space Gods) champion/trait data
- Self-evolving AI agent with LLM decision engine and game memory

## License

GPL-3.0 (inherited from TFT-OCR-BOT)
