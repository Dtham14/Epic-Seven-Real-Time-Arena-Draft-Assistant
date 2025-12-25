# Epic Seven RTA Draft Assistant - User Guide

## Quick Start

1. **Set Pre-Bans**
   - Select 2 heroes you want to pre-ban (My Pre-bans)
   - Select 2 heroes the enemy pre-banned (Enemy Pre-bans)

2. **First Pick** (Important!)
   - **If YOU go first:** Pick your hero (My Pick 1), then click "UPDATE DRAFT" to get defensive follow-up suggestions
   - **If ENEMY goes first:** Select enemy's first pick (Enemy Pick 1), then click "UPDATE DRAFT" to get counter-pick suggestions

3. **Continue Draft Phase**
   - Select heroes as they're picked during the draft
   - Click "UPDATE DRAFT" after enemy picks to get 1-2 AI recommendations
   - The system automatically detects who has first pick based on your selections

4. **Win Prediction**
   - After all 10 heroes are picked, click "Calculate Win Chance"
   - Shows predicted win probability based on team compositions

## Draft Order

### Enemy First Pick
```
e1 → m1,m2 → e2,e3 → m3,m4 → e4,e5 → m5
```
- After enemy picks 1st hero: Get m1+m2 suggestions (pick 2)
- After enemy picks 3rd hero: Get m3+m4 suggestions (pick 2)
- After enemy picks 5th hero: Get m5 suggestion (pick 1)

### You First Pick
```
m1 → e1,e2 → m2,m3 → e3,e4 → m4,m5 → e5
```
- After you pick 1st hero: Wait for enemy to pick 2
- After enemy picks 2nd hero: Get m2+m3 suggestions (pick 2)
- After enemy picks 4th hero: Get m4+m5 suggestions (pick 2)

## Tips

- **Update Draft** button shows recommendations in real-time
- Pre-banned heroes are never recommended
- Already-picked heroes are excluded from suggestions
- Recommendations consider both counters AND team synergy
- Based on 51,680 real RTA matches from all servers

## How It Works

1. **Pattern Matching**: Finds what top players picked in similar situations
2. **Counter Analysis**: Suggests heroes strong against enemy team
3. **Synergy Check**: Recommends heroes that work well with your team
4. **Hybrid System**: Combines all three for best results

---

*Powered by AI analysis of 51,680+ ranked RTA matches*
