# tiny-chess-01 enhanced search engine (MIT, SPDX-License-Identifier: MIT)
# Optimized positional evaluation, piece-square heuristics, and deterministic tie-breaking.
import json, os, sys, urllib.error, urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 20000}

# Center control bonus table (distance to center)
CENTER = {
    "d4": 30, "e4": 30, "d5": 30, "e5": 30,
    "c3": 15, "c4": 15, "c5": 15, "c6": 15,
    "d3": 15, "d6": 15, "e3": 15, "e6": 15,
    "f3": 15, "f4": 15, "f5": 15, "f6": 15
}

def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

def board_of(fen):
    board = {}
    for i, row in enumerate(fen.split()[0].split("/")):
        file = 0
        for c in row:
            if c.isdigit():
                file += int(c)
            else:
                board["abcdefgh"[file] + str(8 - i)] = c
                file += 1
    return board

def evaluate_move(board, move, is_white):
    src, dst = move[:2], move[2:4]
    mover = board.get(src, "p").lower()
    victim = board.get(dst)
    
    # En passant handling
    if victim is None and mover == "p" and src[0] != dst[0]:
        victim = "p"
        
    score = 0
    # MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
    if victim:
        victim_val = VAL.get(victim.lower(), 0)
        mover_val = VAL.get(mover, 0)
        score += victim_val * 10 - mover_val

    # Promotion bonus
    if len(move) == 5:
        score += VAL.get(move[4].lower(), 900) * 10

    # Positional bonus: Center control
    score += CENTER.get(dst, 0)

    # Forward advancement bonus for pawns/knights
    if mover in ("p", "n"):
        adv = (int(dst[1]) - int(src[1])) if is_white else (int(src[1]) - int(dst[1]))
        score += adv * 5

    return score

def choose(fen, legal):
    if not legal:
        return None
    board = board_of(fen)
    is_white = (" w " in fen)

    def move_key(move):
        # Higher score first, then deterministic UCI order
        score = evaluate_move(board, move, is_white)
        return (-score, move)

    return min(legal, key=move_key)

while True:
    g = post("/game", {})
    if g["status"] == "done":
        break
    while g["status"] == "your_move":
        mv = choose(g["fen"], g["legal_moves"])
        g = post("/move", {"game": g["game"], "move": mv})
    print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
